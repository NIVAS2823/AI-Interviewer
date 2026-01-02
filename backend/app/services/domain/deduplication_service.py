"""
Question Deduplication Service
Detects and filters duplicate or similar questions
"""
from typing import List, Set
import logging
from difflib import SequenceMatcher

from app.models.interview import Question
from app.utils.conversation_utils import normalize_message
from app.models.interview import ConversationMessage

logger = logging.getLogger(__name__)


class DeduplicationService:
    """
    Service for detecting and filtering duplicate questions
    Uses multiple strategies: exact match, prefix match, fuzzy similarity
    """

    def __init__(self, similarity_threshold: float = 0.85):
        """
        Initialize deduplication service
        
        Args:
            similarity_threshold: Threshold for fuzzy matching (0-1)
        """
        self.similarity_threshold = similarity_threshold

    def filter_duplicate_questions(
        self,
        questions: List[Question],
        asked_questions: List[str],
        conversation_history: List[dict] = None,
    ) -> List[Question]:
        """
        Filter out duplicate questions using multiple strategies
        
        Args:
            questions: List of Question objects to filter
            asked_questions: List of previously asked question texts
            conversation_history: Optional conversation history for context
            
        Returns:
            Filtered list of unique questions
        """
        if not questions:
            return []

        # Extract questions from conversation history
        conv_questions = self._extract_questions_from_conversation(conversation_history or [])
        
        # Combine all previously asked questions
        all_asked = asked_questions + conv_questions
        
        # Normalize asked questions
        asked_normalized = [self._normalize_text(q) for q in all_asked]
        
        unique_questions = []
        seen_texts = set()

        for question in questions:
            if not question.question_text:
                continue

            q_text = question.question_text.strip()
            q_normalized = self._normalize_text(q_text)

            # Strategy 1: Exact match (normalized)
            if q_normalized in asked_normalized:
                logger.debug(f"⛔ Exact duplicate: {q_text[:60]}...")
                continue

            # Strategy 2: Check against already selected questions in this batch
            if q_normalized in seen_texts:
                logger.debug(f"⛔ Duplicate in batch: {q_text[:60]}...")
                continue

            # Strategy 3: Prefix matching (first 6 words)
            if self._is_prefix_duplicate(q_text, all_asked):
                logger.debug(f"⛔ Prefix duplicate: {q_text[:60]}...")
                continue

            # Strategy 4: Fuzzy similarity matching
            if self._is_fuzzy_duplicate(q_text, all_asked):
                logger.debug(f"⛔ Fuzzy duplicate: {q_text[:60]}...")
                continue

            # Question is unique!
            unique_questions.append(question)
            seen_texts.add(q_normalized)

        logger.info(
            f"✅ Deduplication: {len(questions)} → {len(unique_questions)} "
            f"(removed {len(questions) - len(unique_questions)})"
        )

        return unique_questions

    def _normalize_text(self, text: str) -> str:
        """
        Normalize text for comparison
        
        Args:
            text: Text to normalize
            
        Returns:
            Normalized text
        """
        # Convert to lowercase, strip, remove extra spaces
        normalized = text.lower().strip()
        normalized = ' '.join(normalized.split())
        
        # Remove common punctuation
        for char in ['?', '.', '!', ',', ';', ':']:
            normalized = normalized.replace(char, '')
        
        return normalized

    def _is_prefix_duplicate(self, text: str, asked_questions: List[str]) -> bool:
        """
        Check if question starts similarly to any asked question
        
        Args:
            text: Question text to check
            asked_questions: Previously asked questions
            
        Returns:
            True if prefix duplicate found
        """
        text_words = self._normalize_text(text).split()[:6]
        
        if len(text_words) < 4:
            return False

        for asked in asked_questions:
            asked_words = self._normalize_text(asked).split()[:6]
            
            if len(asked_words) >= 4 and text_words[:4] == asked_words[:4]:
                return True

        return False

    def _is_fuzzy_duplicate(self, text: str, asked_questions: List[str]) -> bool:
        """
        Check if question is too similar to any asked question
        
        Args:
            text: Question text to check
            asked_questions: Previously asked questions
            
        Returns:
            True if fuzzy duplicate found
        """
        text_normalized = self._normalize_text(text)
        
        for asked in asked_questions:
            asked_normalized = self._normalize_text(asked)
            
            # Calculate similarity ratio
            similarity = SequenceMatcher(None, text_normalized, asked_normalized).ratio()
            
            if similarity >= self.similarity_threshold:
                logger.debug(f"   Similarity: {similarity:.2f} with: {asked[:60]}...")
                return True

        return False


    def _extract_questions_from_conversation(self, conversation: List) -> List[str]:
        """
        Extract AI questions from conversation history.
        Supports dicts and ConversationMessage objects safely.
        """
        questions: List[str] = []

        for msg in conversation:
            try:
                normalized = normalize_message(msg)
                speaker = normalized["speaker"]
                text = normalized["text"]

                logger.debug(
                    f"[DEDUP] Processing message | type={type(msg).__name__} "
                    f"speaker={speaker} text_preview={repr(text[:50]) if text else None}"
                )

                # Extract AI/interviewer messages only
                if speaker in {"ai", "assistant", "interviewer"}:
                    if text and len(text.strip()) > 10:
                        questions.append(text.strip())

            except Exception as e:
                logger.warning(
                    f"[DEDUP] Failed to process message of type {type(msg)}: {e}"
                )

        return questions

    

    def detect_question_patterns(self, questions: List[Question]) -> dict:
        """
        Analyze questions for repetitive patterns
        
        Args:
            questions: List of questions to analyze
            
        Returns:
            Dict with pattern statistics
        """
        if not questions:
            return {"patterns": {}, "repetitive": False}

        # Extract starting phrases
        starting_phrases = {}
        
        for q in questions:
            if not q.question_text:
                continue
                
            words = q.question_text.strip().split()[:3]
            phrase = ' '.join(words).lower()
            
            starting_phrases[phrase] = starting_phrases.get(phrase, 0) + 1

        # Find repetitive patterns (used more than once)
        repetitive_patterns = {k: v for k, v in starting_phrases.items() if v > 1}

        return {
            "total_questions": len(questions),
            "unique_patterns": len(starting_phrases),
            "repetitive_patterns": repetitive_patterns,
            "repetitive": len(repetitive_patterns) > 0,
            "diversity_score": len(starting_phrases) / len(questions) if questions else 0,
        }

    def calculate_question_diversity(self, questions: List[Question]) -> float:
        """
        Calculate diversity score for a set of questions
        
        Args:
            questions: List of questions
            
        Returns:
            Diversity score (0-1, higher is more diverse)
        """
        if len(questions) <= 1:
            return 1.0

        # Calculate average pairwise similarity
        total_similarity = 0
        comparisons = 0

        for i in range(len(questions)):
            for j in range(i + 1, len(questions)):
                text1 = self._normalize_text(questions[i].question_text)
                text2 = self._normalize_text(questions[j].question_text)
                
                similarity = SequenceMatcher(None, text1, text2).ratio()
                total_similarity += similarity
                comparisons += 1

        if comparisons == 0:
            return 1.0

        avg_similarity = total_similarity / comparisons
        
        # Diversity is inverse of similarity
        diversity = 1.0 - avg_similarity

        return diversity

    def rank_questions_by_uniqueness(
        self,
        questions: List[Question],
        asked_questions: List[str],
    ) -> List[tuple[Question, float]]:
        """
        Rank questions by how unique they are compared to asked questions
        
        Args:
            questions: Questions to rank
            asked_questions: Previously asked questions
            
        Returns:
            List of (question, uniqueness_score) tuples, sorted by score descending
        """
        ranked = []

        asked_normalized = [self._normalize_text(q) for q in asked_questions]

        for question in questions:
            if not question.question_text:
                continue

            q_normalized = self._normalize_text(question.question_text)

            # Calculate average dissimilarity from all asked questions
            if not asked_normalized:
                uniqueness = 1.0
            else:
                similarities = [
                    SequenceMatcher(None, q_normalized, asked_norm).ratio()
                    for asked_norm in asked_normalized
                ]
                avg_similarity = sum(similarities) / len(similarities)
                uniqueness = 1.0 - avg_similarity

            ranked.append((question, uniqueness))

        # Sort by uniqueness (descending)
        ranked.sort(key=lambda x: x[1], reverse=True)

        return ranked