from typing import Callable

class IOSYSQuery:
    # key_words 为查找关键词及其权重，ref_files 为按关联度查询的相关文件及其权重。
    # 两类权重共用，即，如果 key_words 和 ref_files 各有一个项，而 key_words 中的项权重为 1，
    # ref_files 中的项权重为 0.1，则返回的结果应当倾向于以 key_words 的查询结果为主。
    base_path: str = "."
    key_words: dict[str, float] = {}
    ref_files: dict[str, float] = {}
    constraint: Callable[[str], bool] = lambda x: True
    max_results: int = 10

class IOSYSResponse:
    file_list: list[str] = []
    weights: list[float] = []
    description: list[str] = []

class IOSYSRetriever:
    def retrieve(self, query: IOSYSQuery) -> IOSYSResponse:
        raise NotImplementedError("This method is not implemented yet.")