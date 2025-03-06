import re
import math
from typing import Dict, List, Tuple

class ReadabilityAnalyzer:
    """Service for computing readability metrics for regulatory documents"""
    
    @staticmethod
    def count_syllables(word: str) -> int:
        """
        Count the number of syllables in a word using a basic heuristic approach.
        """
        if not word or not isinstance(word, str):
            return 1  # Return minimum syllable count for invalid input
            
        word = word.lower().strip()
        if not word:
            return 1
            
        count = 0
        vowels = "aeiouy"
        
        # Handle special cases
        if word.endswith("e"):
            word = word[:-1]
        
        # Count vowel groups
        prev_char = None
        for i, char in enumerate(word):
            if not isinstance(char, str):
                continue  # Skip non-string characters
            if char in vowels and (i == 0 or word[i-1] not in vowels):
                count += 1
        
        return max(1, count)  # Every word has at least one syllable
    
    @staticmethod
    def get_sentences(text: str) -> List[str]:
        """Split text into sentences."""
        # Basic sentence splitting on common end punctuation
        sentences = re.split(r'[.!?]+', text)
        return [s.strip() for s in sentences if s.strip()]
    
    @staticmethod
    def get_words(text: str) -> List[str]:
        """Split text into words."""
        return re.findall(r'\b\w+\b', text.lower())
    
    @staticmethod
    def count_complex_words(words: List[str]) -> int:
        """Count words with 3 or more syllables."""
        return sum(1 for word in words if ReadabilityAnalyzer.count_syllables(word) >= 3)
    
    @classmethod
    def compute_flesch_reading_ease(cls, text: str) -> float:
        """
        Compute the Flesch Reading Ease score.
        Score range: 0-100 (higher is more readable)
        """
        sentences = cls.get_sentences(text)
        words = cls.get_words(text)
        
        if not words or not sentences:
            return 0.0
        
        total_syllables = sum(cls.count_syllables(word) for word in words)
        words_per_sentence = len(words) / len(sentences)
        syllables_per_word = total_syllables / len(words)
        
        score = 206.835 - (1.015 * words_per_sentence) - (84.6 * syllables_per_word)
        return max(0.0, min(100.0, score))
    
    @classmethod
    def compute_smog_index(cls, text: str) -> float:
        """
        Compute SMOG Index (Simple Measure of Gobbledygook).
        Score range: typically 6-20 (lower is more readable)
        """
        sentences = cls.get_sentences(text)
        words = cls.get_words(text)
        
        if len(sentences) < 30 or not words:
            return 0.0
        
        complex_word_count = cls.count_complex_words(words)
        score = 1.0430 * math.sqrt(complex_word_count * (30 / len(sentences))) + 3.1291
        
        # Normalize to 0-100 scale (assuming range of 6-20)
        normalized_score = 100 - ((score - 6) * (100 / 14))
        return max(0.0, min(100.0, normalized_score))
    
    @classmethod
    def compute_ari(cls, text: str) -> float:
        """
        Compute Automated Readability Index.
        Score range: typically 1-14 (lower is more readable)
        """
        sentences = cls.get_sentences(text)
        words = cls.get_words(text)
        characters = len(re.sub(r'\s', '', text))
        
        if not words or not sentences:
            return 0.0
        
        score = 4.71 * (characters / len(words)) + 0.5 * (len(words) / len(sentences)) - 21.43
        
        # Normalize to 0-100 scale (assuming range of 1-14)
        normalized_score = 100 - ((score - 1) * (100 / 13))
        return max(0.0, min(100.0, normalized_score))
    
    @classmethod
    def compute_readability_score(cls, text: str) -> Tuple[float, Dict[str, float]]:
        """
        Compute a combined readability score and individual metrics.
        Returns a tuple of (combined_score, detailed_metrics)
        
        The combined score is weighted average of:
        - Flesch Reading Ease (50%)
        - SMOG Index (25%)
        - ARI (25%)
        
        All scores are normalized to 0-100 scale where higher means more readable.
        """
        if not text or not text.strip():
            return 0.0, {
                "flesch_reading_ease": 0.0,
                "smog_index": 0.0,
                "automated_readability_index": 0.0
            }
        
        # Compute individual scores
        flesch_score = cls.compute_flesch_reading_ease(text)
        smog_score = cls.compute_smog_index(text)
        ari_score = cls.compute_ari(text)
        
        # Compute weighted average
        combined_score = (
            (flesch_score * 0.5) +
            (smog_score * 0.25) +
            (ari_score * 0.25)
        )
        
        metrics = {
            "flesch_reading_ease": flesch_score,
            "smog_index": smog_score,
            "automated_readability_index": ari_score
        }
        
        return combined_score, metrics 