"""
FSRS (Free Spaced Repetition Scheduler) integration for Homeschool.
Provides spaced repetition scheduling for Anki cards.
"""

from typing import Optional, Dict, Any
from datetime import datetime, timedelta
from dataclasses import dataclass

from .logging import get_logger

logger = get_logger(__name__)

# Try to import py-fsrs, fall back to basic implementation
try:
    from fsrs import FSRS, Card, ReviewLog
    FSRS_AVAILABLE = True
except ImportError:
    FSRS_AVAILABLE = False
    logger.warning("py-fsrs not available, using basic scheduling")


@dataclass
class FSRSParameters:
    """FSRS algorithm parameters."""
    request_retention: float = 0.9
    enable_bonuses: bool = True
    enable_fuzzing: bool = True


class FSRSConfig:
    """Configuration presets for FSRS scheduling."""
    
    AGGRESSIVE = FSRSParameters(request_retention=0.95)
    BALANCED = FSRSParameters(request_retention=0.90)
    CONSERVATIVE = FSRSParameters(request_retention=0.85)


class FSRSScheduler:
    """
    FSRS scheduler wrapper for Homeschool.
    Provides spaced repetition scheduling with configurable presets.
    """

    def __init__(self, preset: str = "balanced", params: Optional[FSRSParameters] = None):
        """
        Initialize the FSRS scheduler.
        
        Args:
            preset: Preset name ('aggressive', 'balanced', 'conservative')
            params: Custom FSRS parameters
        """
        self.preset = preset.lower() if preset else "balanced"
        
        if params:
            self.params = params
        elif self.preset == "aggressive":
            self.params = FSRSConfig.AGGRESSIVE
        elif self.preset == "conservative":
            self.params = FSRSConfig.CONSERVATIVE
        else:
            self.params = FSRSConfig.BALANCED
        
        self._fsrs = None
        if FSRS_AVAILABLE:
            try:
                self._fsrs = FSRS(
                    request_retention=self.params.request_retention,
                    enable_bonuses=self.params.enable_bonuses,
                    enable_fuzzing=self.params.enable_fuzzing
                )
                logger.info("Initialized FSRS scheduler", preset=self.preset)
            except Exception as e:
                logger.error("Failed to initialize FSRS", error=str(e))

    def get_next_review_date(self, quality: int = 3) -> datetime:
        """
        Get the next review date based on FSRS algorithm.
        
        Args:
            quality: Review quality (0-5 in Anki scale, converted to FSRS)
                     0-2: Again (fail)
                     3: Hard
                     4: Good
                     5: Easy
        
        Returns:
            Datetime of next review
        """
        if not self._fsrs:
            # Fallback to basic scheduling
            intervals = {
                0: 1,    # 1 minute
                1: 10,   # 10 minutes
                2: 1440, # 1 day
                3: 4320, # 3 days
                4: 10080, # 7 days
                5: 43200  # 30 days
            }
            minutes = intervals.get(quality, 1440)
            return datetime.now() + timedelta(minutes=minutes)
        
        try:
            card = Card()
            card.reps = 0
            card.due = datetime.now()
            
            # Convert Anki quality to FSRS rating (0-3)
            # Anki: 0,1,2 = Again, 3=Hard, 4=Good, 5=Easy
            # FSRS: 0=Again, 1=Hard, 2=Good, 3=Easy
            rating = min(max(quality - 2, 0), 3) if quality >= 3 else 0
            
            review_log = self._fsrs.review_card(card, rating)
            
            return review_log.due
            
        except Exception as e:
            logger.error("FSRS review calculation failed", error=str(e))
            return datetime.now() + timedelta(days=1)

    def get_interval_days(self, quality: int = 3) -> int:
        """
        Get interval in days for Anki scheduling.
        
        Args:
            quality: Review quality
            
        Returns:
            Interval in days (for Anki interval field)
        """
        if not self._fsrs:
            intervals = {0: 1, 1: 1, 2: 1, 3: 3, 4: 7, 5: 30}
            return intervals.get(quality, 1)
        
        try:
            card = Card()
            card.reps = 0
            
            rating = min(max(quality - 2, 0), 3) if quality >= 3 else 0
            review_log = self._fsrs.review_card(card, rating)
            
            # Get interval in days
            if review_log.interval:
                return round(review_log.interval / 1440)  # minutes to days
            
        except Exception:
            pass
        
        return 1

    def create_fsrs_fields(self, quality: int = 3) -> Dict[str, Any]:
        """
        Create Anki-compatible FSRS fields for card creation.
        
        Args:
            quality: Review quality for initial scheduling
            
        Returns:
            Dict of FSRS fields for Anki card
        """
        if not self._fsrs:
            return {
                "Minimum_interval": 1,
                "Maximum_interval": 36500,
                "Ease_bonus": "130%"
            }
        
        try:
            from fsrs import SchedulerItem
            item = SchedulerItem(
                due=datetime.now(),
                rep=0,
                lapses=0,
                state=0,
                interval=0,
                ease_factor=2500,
                timer=0,
            )
            self._fsrs.schedule(item)
            
            return {
                "Minimum_interval": str(item.interval),
                "Maximum_interval": "36500",  # 100 years
                "Ease_bonus": f"{self._fsrs.ease_bonus * 100:.0f}%"
            }
        except Exception:
            return {
                "Minimum_interval": "1",
                "Maximum_interval": "36500",
                "Ease_bonus": "130%"
            }


def create_scheduler(preset: str = "balanced") -> FSRSScheduler:
    """
    Factory function to create an FSRS scheduler.
    
    Args:
        preset: Scheduling preset ('aggressive', 'balanced', 'conservative')
        
    Returns:
        Configured FSRSScheduler instance
    """
    return FSRSScheduler(preset=preset)
