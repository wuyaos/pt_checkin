import base64
import hashlib
import hmac
import struct
import time


class GoogleAuthenticator:
    @staticmethod
    def calc_code(secret_key: str) -> str:
        """
        Calculate the Google Authenticator code.
        """
        input_time = int(time.time()) // 30
        key = base64.b32decode(secret_key, True)
        msg = struct.pack(">Q", input_time)
        google_code = hmac.new(key, msg, hashlib.sha1).digest()
        o = google_code[19] & 15
        google_code_int = (struct.unpack(">I", google_code[o:o + 4])[0] &
                           0x7fffffff)
        google_code_str = str(google_code_int % 1000000)
        return google_code_str.zfill(6)

