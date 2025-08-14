"""
HTML解析工具模块
替代FlexGet的soup工具，使用BeautifulSoup4实现
"""

from typing import Union
from bs4 import BeautifulSoup


def get_soup(html_content: Union[str, bytes], parser: str = 'html.parser') -> BeautifulSoup:
    """
    解析HTML内容，返回BeautifulSoup对象
    
    这个函数替代了FlexGet的flexget.utils.soup.get_soup函数
    
    Args:
        html_content: HTML内容，可以是字符串或字节
        parser: 解析器类型，默认使用'html.parser'
                可选: 'html.parser', 'lxml', 'html5lib'
    
    Returns:
        BeautifulSoup: 解析后的BeautifulSoup对象
    
    Examples:
        >>> html = '<div class="test">Hello</div>'
        >>> soup = get_soup(html)
        >>> soup.select_one('.test').text
        'Hello'
    """
    return BeautifulSoup(html_content, parser)
