"""tqdm用のユーティリティ集。"""

import logging

import tqdm


class TqdmStreamHandler(logging.StreamHandler):
    """tqdm対応のStreamHandler。

    使用例::
        import pytilpack.tqdm_

        logging.basicConfig(
            level=logging.INFO,
            format="[%(levelname)s] %(message)s",
            handlers=[pytilpack.tqdm_.TqdmStreamHandler()],
        )

    """

    def emit(self, record):
        with tqdm.tqdm.external_write_mode(file=self.stream):
            super().emit(record)
