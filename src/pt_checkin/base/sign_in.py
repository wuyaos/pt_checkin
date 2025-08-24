from __future__ import annotations

import re
from abc import ABC, abstractmethod

from ..base.log_manager import get_logger

logger = get_logger(__name__)
from requests import Response

from ..core.entry import SignInEntry
from ..utils.common_utils import NetworkState, SignState
from .request import check_network_state
from .work import Work


def check_state(
    entry: SignInEntry,
    work: Work,
    response: Response | None,
    content: str | None,
) -> bool:
    if entry.failed:
        return False
    if not work.assert_state:
        return True
    check_method, state = work.assert_state
    return check_method(entry, work, response, content) == state


def check_sign_in_state(
    entry: SignInEntry,
    work: Work,
    response: Response | None,
    content: str | None,
) -> NetworkState | SignState:
    if (
        network_state := check_network_state(
            entry, work, response, content=content, check_content=True
        )
    ) != NetworkState.SUCCEED:
        return network_state
    if not (succeed_regex := work.succeed_regex):
        entry["result"] = SignState.SUCCEED.value + entry.get("extra_msg", "")
        return SignState.SUCCEED
    for regex in succeed_regex:
        if isinstance(regex, str):
            regex = (regex, 0)
        regex, group_index = regex
        if succeed_msg := re.search(regex, content):
            entry["result"] = (
                re.sub("<.*?>|&shy;|&nbsp;", "", succeed_msg.group(group_index))
                + entry["result"]
                + entry.get("extra_msg", "")
            )
            return SignState.SUCCEED
    if (fail_regex := work.fail_regex) and re.search(fail_regex, content):
        return SignState.WRONG_ANSWER
    # 检查网络错误模式
    network_error_patterns = [
        NetworkState.DDOS_PROTECTION_BY_CLOUDFLARE,
        NetworkState.SERVER_LOAD_TOO_HIGH,
        NetworkState.CONNECTION_TIMED_OUT,
        NetworkState.THE_WEB_SERVER_REPORTED_A_BAD_GATEWAY_ERROR,
        NetworkState.WEB_SERVER_IS_DOWN,
        NetworkState.INCORRECT_CSRF_TOKEN,
    ]

    for error_pattern in network_error_patterns:
        if re.search(error_pattern.value, content):
            entry.fail_with_prefix(
                NetworkState.NETWORK_ERROR.value.format(
                    url=work.url, error=error_pattern.name.title()
                )
            )
            return NetworkState.NETWORK_ERROR
    if (assert_state := work.assert_state) and assert_state[1] != SignState.NO_SIGN_IN:
        logger.warning(f"no sign in, regex: {succeed_regex}, content: {content}")
    return SignState.NO_SIGN_IN


def check_final_state(
    entry: SignInEntry,
    work: Work,
    response: Response,
    content: str,
) -> SignState:
    if (
        sign_in_state := check_sign_in_state(entry, work, response, content)
    ) == SignState.NO_SIGN_IN:
        entry.fail_with_prefix(SignState.SIGN_IN_FAILED.value.format("no sign in"))
        return SignState.SIGN_IN_FAILED
    return sign_in_state


class SignIn(ABC):
    @classmethod
    @abstractmethod
    def sign_in_build_schema(cls) -> dict:
        pass

    @classmethod
    @abstractmethod
    def sign_in_build_entry(cls, entry: SignInEntry, config: dict) -> None:
        pass

    @abstractmethod
    def sign_in(self, entry: SignInEntry, config: dict) -> None:
        pass
