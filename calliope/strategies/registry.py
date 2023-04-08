from typing import Any, Callable, cast, Dict, Sequence, Type

from calliope.strategies.base import StoryStrategy


class StoryStrategyRegistry:
    """
    A registry of story strategy classes.
    """

    # All registered block classes, keyed by block type.
    _story_strategies_by_name: Dict[str, Type] = {}

    @classmethod
    def register(cls) -> Callable:
        """
        Registers a block model class, along with valid and invalid example attribute
        dictionaries.
        """

        def register_strategy(strategy_class: Type) -> Callable[[Type[Any]], Type[Any]]:
            strategy_name = strategy_class.strategy_name
            if not strategy_name:
                raise ValueError(f"strategy_name not set for strategy: {strategy_class}")

            cls._story_strategies_by_name[strategy_name] = strategy_class
            return strategy_class

        return register_strategy

    @classmethod
    def get_strategy_class(cls, strategy_name: str) -> Type[StoryStrategy]:
        """
        Gets the block class for a given block type.

        Returns:
            The block class.
        Raises:
            ValueError if the block class isn't found.
        """
        if strategy_name not in cls._story_strategies_by_name:
            raise ValueError(f"Unknown story strategy: {strategy_name}")
        return cls._story_strategies_by_name[strategy_name]

    @classmethod
    def get_all_strategy_names(cls) -> Sequence[str]:
        return cls._story_strategies_by_name.keys()
