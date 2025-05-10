from markitdown import MarkItDown

md = MarkItDown(enable_plugins=True) # Set to True to enable plugins
result = md.convert("./third/markitdown/tests/test_files/test.xlsx")
print(result.text_content)
