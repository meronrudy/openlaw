"""
HuggingFace Ingestion Pipeline for CAP Caselaw Plugin
Streams and processes 37M+ legal documents from Harvard CAP dataset
"""

import logging
import asyncio
from typing import Dict, List, Any, Optional, Iterator, AsyncIterator
from datetime import datetime
from dataclasses import dataclass, field
from pathlib import Path
import json
import time

try:
    from datasets import load_dataset, Dataset, IterableDataset
    from transformers import AutoTokenizer
    HF_AVAILABLE = True
except ImportError:
    HF_AVAILABLE = False
    logging.warning("HuggingFace datasets/transformers not available. Install with: pip install datasets transformers")

from ..models.canonical_identifiers import DocumentID, IDGenerator
from ..models.provenance_record import ProvenanceRecord, ProvenanceOperation, ProvenanceSource
from ..extraction.citation_extractor import CitationExtractor, MLCitationExtractor
from ..extraction.relationship_extractor import CaseRelationshipExtractor

logger = logging.getLogger(__name__)


@dataclass
class IngestionStats:
    """Statistics for ingestion process"""
    total_processed: int = 0
    successful_ingestions: int = 0
    failed_ingestions: int = 0
    citations_extracted: int = 0
    relationships_identified: int = 0
    processing_rate: float = 0.0  # docs per second
    start_time: datetime = field(default_factory=datetime.utcnow)
    last_update: datetime = field(default_factory=datetime.utcnow)
    
    def update_rate(self):
        """Update processing rate"""
        elapsed = (datetime.utcnow() - self.start_time).total_seconds()
        if elapsed > 0:
            self.processing_rate = self.total_processed / elapsed
        self.last_update = datetime.utcnow()
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_processed": self.total_processed,
            "successful_ingestions": self.successful_ingestions,
            "failed_ingestions": self.failed_ingestions,
            "citations_extracted": self.citations_extracted,
            "relationships_identified": self.relationships_identified,
            "processing_rate": self.processing_rate,
            "start_time": self.start_time.isoformat(),
            "last_update": self.last_update.isoformat(),
            "success_rate": self.successful_ingestions / max(self.total_processed, 1)
        }


@dataclass
class ProcessedCase:
    """Represents a processed case ready for storage"""
    case_id: DocumentID
    raw_data: Dict[str, Any]
    extracted_citations: List[Dict[str, Any]]
    case_relationships: List[Dict[str, Any]]
    metadata: Dict[str, Any]
    provenance: ProvenanceRecord
    processing_time: float
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "case_id": str(self.case_id),
            "raw_data": self.raw_data,
            "extracted_citations": self.extracted_citations,
            "case_relationships": self.case_relationships,
            "metadata": self.metadata,
            "provenance": self.provenance.to_dict(),
            "processing_time": self.processing_time
        }


class HuggingFaceIngestionPipeline:
    """
    Streams and processes Harvard CAP dataset from HuggingFace
    """
    
    def __init__(self, store=None, citation_extractor=None, relationship_extractor=None,
                 batch_size: int = 1000, max_workers: int = 10, 
                 dataset_name: str = "harvard-lil/cap-us-court-opinions"):
        """
        Initialize ingestion pipeline
        
        Args:
            store: Storage backend for processed data
            citation_extractor: Citation extraction component
            relationship_extractor: Relationship extraction component  
            batch_size: Number of documents to process in each batch
            max_workers: Maximum concurrent workers
            dataset_name: HuggingFace dataset identifier
        """
        if not HF_AVAILABLE:
            raise ImportError("HuggingFace libraries required. Install with: pip install datasets transformers")
        
        self.store = store
        self.citation_extractor = citation_extractor or MLCitationExtractor()
        self.relationship_extractor = relationship_extractor or CaseRelationshipExtractor()
        self.batch_size = batch_size
        self.max_workers = max_workers
        self.dataset_name = dataset_name
        
        # Processing components
        self.id_generator = IDGenerator()
        self.stats = IngestionStats()
        self._processing_queue = asyncio.Queue(maxsize=batch_size * 2)
        self._workers_running = False
        self._stop_processing = False
        
        # Configuration
        self.resume_from_checkpoint = True
        self.checkpoint_frequency = 1000  # Save progress every N documents
        self.retry_failed = True
        self.max_retries = 3
        
    async def start_streaming_ingestion(self, subset: Optional[str] = None,
                                      resume_from: Optional[int] = None,
                                      max_documents: Optional[int] = None) -> AsyncIterator[IngestionStats]:
        """
        Start streaming ingestion from HuggingFace dataset
        
        Args:
            subset: Dataset subset to process (e.g., "train", "test")
            resume_from: Document index to resume from
            max_documents: Maximum number of documents to process
            
        Yields:
            Ingestion statistics at regular intervals
        """
        logger.info(f"Starting HuggingFace ingestion from {self.dataset_name}")
        
        try:
            # Load dataset in streaming mode
            dataset = await self._load_streaming_dataset(subset)
            
            # Start background workers
            await self._start_background_workers()
            
            # Process documents
            doc_count = 0
            resume_point = resume_from or 0
            
            async for batch in self._stream_batches(dataset, resume_point, max_documents):
                # Queue batch for processing
                await self._processing_queue.put(batch)
                
                doc_count += len(batch)
                self.stats.total_processed = doc_count
                self.stats.update_rate()
                
                # Yield stats periodically
                if doc_count % 100 == 0:  # Every 100 documents
                    yield self.stats
                
                # Check if we should stop
                if self._stop_processing:
                    break
                
                # Checkpoint periodically
                if doc_count % self.checkpoint_frequency == 0:
                    await self._save_checkpoint(doc_count)
            
            # Process remaining items in queue
            await self._flush_processing_queue()
            
            # Final stats
            self.stats.update_rate()
            yield self.stats
            
        except Exception as e:
            logger.error(f"Error in streaming ingestion: {e}")
            raise
        finally:
            await self._stop_background_workers()
    
    async def _load_streaming_dataset(self, subset: Optional[str] = None) -> IterableDataset:
        """Load HuggingFace dataset in streaming mode"""
        try:
            logger.info(f"Loading dataset {self.dataset_name} in streaming mode")
            
            # Load in streaming mode for memory efficiency
            dataset = load_dataset(
                self.dataset_name,
                split=subset or "train",
                streaming=True,
                trust_remote_code=True
            )
            
            logger.info("Dataset loaded successfully")
            return dataset
            
        except Exception as e:
            logger.error(f"Failed to load dataset {self.dataset_name}: {e}")
            raise
    
    async def _stream_batches(self, dataset: IterableDataset, 
                            resume_from: int = 0, 
                            max_documents: Optional[int] = None) -> AsyncIterator[List[Dict[str, Any]]]:
        """Stream documents in batches"""
        batch = []
        doc_count = 0
        
        for document in dataset:
            # Skip to resume point
            if doc_count < resume_from:
                doc_count += 1
                continue
            
            batch.append(document)
            doc_count += 1
            
            # Yield batch when full
            if len(batch) >= self.batch_size:
                yield batch
                batch = []
            
            # Check limits
            if max_documents and doc_count >= max_documents:
                break
            
            # Allow other coroutines to run
            if doc_count % 10 == 0:
                await asyncio.sleep(0)
        
        # Yield remaining documents
        if batch:
            yield batch
    
    async def _start_background_workers(self):
        """Start background worker tasks"""
        self._workers_running = True
        self._worker_tasks = []
        
        for i in range(self.max_workers):
            task = asyncio.create_task(self._worker_loop(f"worker-{i}"))
            self._worker_tasks.append(task)
        
        logger.info(f"Started {self.max_workers} background workers")
    
    async def _worker_loop(self, worker_id: str):
        """Main loop for worker processing"""
        logger.debug(f"Worker {worker_id} started")
        
        while self._workers_running:
            try:
                # Get batch from queue with timeout
                batch = await asyncio.wait_for(
                    self._processing_queue.get(), 
                    timeout=1.0
                )
                
                # Process batch
                await self._process_batch(batch, worker_id)
                
                # Mark task as done
                self._processing_queue.task_done()
                
            except asyncio.TimeoutError:
                # No work available, continue polling
                continue
            except Exception as e:
                logger.error(f"Worker {worker_id} error: {e}")
                # Continue processing other batches
                continue
        
        logger.debug(f"Worker {worker_id} stopped")
    
    async def _process_batch(self, batch: List[Dict[str, Any]], worker_id: str):
        """Process a batch of documents"""
        logger.debug(f"Worker {worker_id} processing batch of {len(batch)} documents")
        
        for document in batch:
            try:
                start_time = time.time()
                
                # Process individual document
                processed_case = await self._process_document(document)
                
                # Store processed case
                if processed_case and self.store:
                    await self._store_processed_case(processed_case)
                    self.stats.successful_ingestions += 1
                else:
                    self.stats.failed_ingestions += 1
                
                # Update statistics
                processing_time = time.time() - start_time
                logger.debug(f"Processed case in {processing_time:.2f}s")
                
            except Exception as e:
                logger.error(f"Error processing document: {e}")
                self.stats.failed_ingestions += 1
    
    async def _process_document(self, document: Dict[str, Any]) -> Optional[ProcessedCase]:
        """Process a single legal document"""
        try:
            start_time = time.time()
            
            # Generate canonical ID
            cap_case_id = document.get("id") or document.get("case_id")
            if not cap_case_id:
                logger.warning("Document missing case ID, skipping")
                return None
            
            case_id = self.id_generator.generate_document_id(cap_case_id)
            
            # Extract text content
            full_text = self._extract_text_content(document)
            if not full_text:
                logger.warning(f"No text content found for case {cap_case_id}")
                return None
            
            # Extract citations
            citations = self.citation_extractor.extract_citations(full_text, str(case_id))
            self.stats.citations_extracted += len(citations)
            
            # Extract relationships
            relationships = self.relationship_extractor.extract_relationships(
                full_text, citations, str(case_id)
            )
            self.stats.relationships_identified += len(relationships)
            
            # Create provenance record
            provenance = ProvenanceRecord(
                operation=ProvenanceOperation.EXTRACT,
                source=ProvenanceSource.HUGGINGFACE,
                agent_type="system",
                agent_id="hf_ingestion_pipeline",
                timestamp=datetime.utcnow(),
                confidence=0.9,
                metadata={
                    "dataset": self.dataset_name,
                    "original_id": cap_case_id,
                    "text_length": len(full_text),
                    "citations_found": len(citations),
                    "relationships_found": len(relationships)
                }
            )
            
            # Extract metadata
            metadata = self._extract_metadata(document)
            
            processing_time = time.time() - start_time
            
            return ProcessedCase(
                case_id=case_id,
                raw_data=document,
                extracted_citations=[c.to_dict() for c in citations],
                case_relationships=[r.to_dict() for r in relationships],
                metadata=metadata,
                provenance=provenance,
                processing_time=processing_time
            )
            
        except Exception as e:
            logger.error(f"Error processing document {document.get('id', 'unknown')}: {e}")
            return None
    
    def _extract_text_content(self, document: Dict[str, Any]) -> str:
        """Extract full text content from document"""
        # Try different fields that might contain the case text
        text_fields = [
            "casebody.data.opinions",
            "text",
            "opinion",
            "casebody",
            "full_text"
        ]
        
        full_text = ""
        
        for field in text_fields:
            content = self._get_nested_field(document, field)
            if content:
                if isinstance(content, list):
                    # Handle list of opinions
                    for item in content:
                        if isinstance(item, dict):
                            text = item.get("text", "") or item.get("content", "")
                        else:
                            text = str(item)
                        full_text += f"\n{text}"
                else:
                    full_text += f"\n{str(content)}"
        
        return full_text.strip()
    
    def _extract_metadata(self, document: Dict[str, Any]) -> Dict[str, Any]:
        """Extract metadata from document"""
        metadata = {}
        
        # Standard CAP fields
        metadata_fields = {
            "name": "case_name",
            "name_abbreviation": "case_name_abbreviated", 
            "decision_date": "decision_date",
            "court.name": "court_name",
            "court.slug": "court_slug",
            "jurisdiction.name": "jurisdiction_name",
            "jurisdiction.slug": "jurisdiction_slug",
            "citations": "citations",
            "volume.volume_number": "volume_number",
            "volume.reporter": "reporter",
            "first_page": "first_page",
            "last_page": "last_page"
        }
        
        for field_path, metadata_key in metadata_fields.items():
            value = self._get_nested_field(document, field_path)
            if value is not None:
                metadata[metadata_key] = value
        
        # Add processing metadata
        metadata["processed_at"] = datetime.utcnow().isoformat()
        metadata["source_dataset"] = self.dataset_name
        
        return metadata
    
    def _get_nested_field(self, obj: Dict[str, Any], field_path: str) -> Any:
        """Get nested field value using dot notation"""
        try:
            keys = field_path.split(".")
            value = obj
            for key in keys:
                if isinstance(value, dict):
                    value = value.get(key)
                else:
                    return None
                if value is None:
                    return None
            return value
        except (KeyError, TypeError):
            return None
    
    async def _store_processed_case(self, processed_case: ProcessedCase):
        """Store processed case in storage backend"""
        if not self.store:
            logger.warning("No storage backend configured")
            return
        
        try:
            # Store using hypergraph store interface
            await self.store.store_case(processed_case)
            
        except Exception as e:
            logger.error(f"Error storing case {processed_case.case_id}: {e}")
            raise
    
    async def _flush_processing_queue(self):
        """Wait for all queued items to be processed"""
        await self._processing_queue.join()
    
    async def _stop_background_workers(self):
        """Stop background worker tasks"""
        self._workers_running = False
        
        if hasattr(self, '_worker_tasks'):
            # Cancel all worker tasks
            for task in self._worker_tasks:
                task.cancel()
            
            # Wait for them to finish
            await asyncio.gather(*self._worker_tasks, return_exceptions=True)
        
        logger.info("Background workers stopped")
    
    async def _save_checkpoint(self, doc_count: int):
        """Save processing checkpoint"""
        checkpoint_data = {
            "processed_count": doc_count,
            "timestamp": datetime.utcnow().isoformat(),
            "stats": self.stats.to_dict()
        }
        
        # Save to file or storage
        checkpoint_path = Path(f"checkpoint_cap_ingestion_{doc_count}.json")
        try:
            with open(checkpoint_path, "w") as f:
                json.dump(checkpoint_data, f, indent=2)
            logger.info(f"Checkpoint saved at document {doc_count}")
        except Exception as e:
            logger.error(f"Failed to save checkpoint: {e}")
    
    def stop_processing(self):
        """Signal to stop processing"""
        self._stop_processing = True
        logger.info("Stop signal sent to ingestion pipeline")
    
    async def start_background_processing(self):
        """Start background processing task (for plugin integration)"""
        logger.info("Starting background CAP ingestion processing")
        
        try:
            # Start with a small subset for testing
            async for stats in self.start_streaming_ingestion(max_documents=1000):
                logger.info(f"Ingestion progress: {stats.total_processed} processed, "
                           f"{stats.processing_rate:.2f} docs/sec")
                
                # Sleep between updates
                await asyncio.sleep(10)
                
        except Exception as e:
            logger.error(f"Background processing error: {e}")
        
        logger.info("Background CAP ingestion processing completed")