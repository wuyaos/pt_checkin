"""
通知模块
简单的通知实现，可以根据需要扩展
"""


def send(title: str, content: str):
    """
    发送通知
    
    Args:
        title: 通知标题
        content: 通知内容
    """
    print(f"[通知] {title}")
    print(f"内容: {content}")
    print("-" * 50)
