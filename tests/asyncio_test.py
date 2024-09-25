"""テストコード。"""

import asyncio

import pytilpack.asyncio_


async def async_func():
    await asyncio.sleep(0.0)
    return "Done"


def test_run():
    for _ in range(3):
        assert pytilpack.asyncio_.run(async_func()) == "Done"

    assert tuple(
        pytilpack.asyncio_.run(asyncio.gather(async_func(), async_func(), async_func()))
    ) == ("Done", "Done", "Done")
