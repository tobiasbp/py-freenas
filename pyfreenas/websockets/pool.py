from typing import (
    Any,
    Dict,
    List,
    TypeVar,
)
from ..pool import Pool, PoolStatus

TCachingMachine = TypeVar("TCachingMachine", bound="TCachingMachine")
TCachingPoolStateFetcher = TypeVar(
    "TCachingPoolStateFetcher", bound="CachingPoolStateFetcher"
)


class CachingPool(Pool):
    def __init__(self, fetcher: TCachingPoolStateFetcher, guid: str) -> None:
        self._fetcher = fetcher
        self._guid = guid
        self._cached_state = self._state

    @property
    def available(self) -> bool:
        """If the pool exists on the Machine."""
        return self._guid in self._fetcher._state

    @property
    def encrypt(self) -> int:
        """The encrypt? of the pool."""
        if self.available:
            self._cached_state = self._state
            return self._state["encrypt"]
        return self._cached_state["encrypt"]

    @property
    def guid(self) -> str:
        """The guid of the pool."""
        return self._guid

    @property
    def id(self) -> int:
        """The id of the pool."""
        if self.available:
            self._cached_state = self._state
            return self._state["id"]
        return self._cached_state["id"]

    @property
    def is_decrypted(self) -> bool:
        """Is the pool decrypted?"""
        if self.available:
            self._cached_state = self._state
            return self._state["is_decrypted"]
        return self._cached_state["is_decrypted"]

    @property
    def name(self) -> str:
        """The name of the pool."""
        if self.available:
            self._cached_state = self._state
            return self._state["name"]
        return self._cached_state["name"]

    @property
    def status(self) -> PoolStatus:
        """The status of the pool."""
        if self.available:
            self._cached_state = self._state
            return PoolStatus.fromValue(self._state["status"])
        return PoolStatus.fromValue(self._cached_state["status"])

    @property
    def topology(self) -> dict:
        """The topology of the pool."""
        if self.available:
            self._cached_state = self._state
            return self._state["topology"]
        return self._cached_state["topology"]

    @property
    def _state(self) -> dict:
        """The state of the pool, according to the Machine."""
        return self._fetcher._get_cached_state(self)


class CachingPoolStateFetcher(object):
    _parent: TCachingMachine
    _state: Dict[str, dict]
    _cached_pools: List[CachingPool]

    def __init__(self, machine: TCachingMachine) -> None:
        self._parent = machine
        self._state = {}
        self._cached_pools = []

    async def get_pools(self) -> List[CachingPool]:
        """Returns a list of pools known to the host."""
        self._state = await self._fetch_pools()
        self._update_properties_from_state()
        return self.pools

    @property
    def pools(self) -> List[CachingPool]:
        """Returns a list of pools known to the host."""
        return self._cached_pools

    def _get_cached_state(self, pool: Pool) -> dict:
        return self._state[pool.guid]

    async def _fetch_pools(self) -> Dict[str, dict]:
        assert self._parent._client is not None
        pools = await self._parent._client.invoke_method(
            "pool.query",
            [
                [],
                {
                    "select": [
                        "encrypt",
                        "encryptkey",
                        "guid",
                        "id",
                        "is_decrypted",
                        "name",
                        "status",
                        "topology",
                    ],
                },
            ],
        )
        return {pool["guid"]: pool for pool in pools}

    def _update_properties_from_state(self) -> None:
        available_pools_by_guid = {
            pool.guid: pool for pool in self._cached_pools if pool.available
        }
        current_pool_guids = {pool_guid for pool_guid in self._state}
        pool_guids_to_add = current_pool_guids - set(available_pools_by_guid)
        self._cached_pools = [*available_pools_by_guid.values()] + [
            CachingPool(fetcher=self, guid=pool_guid) for pool_guid in pool_guids_to_add
        ]
