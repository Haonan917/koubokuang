from enum import Enum


class ApiCode(Enum):
    OK = (0, "成功!")
    ERROR = (1, "错误!")
    EXCEPTION = (2, "异常!")
    INVALID_PARAMETER = (3, "无效参数!")
    MISSING_PARAMETER = (4, "缺少参数!")
    FAILED_TO_ADD = (5, "添加记录失败!")
    FAILED_TO_UPDATE = (6, "更新记录失败!")
    EMPTY_RESULT = (7, "结果为空!")
    EXIST_RECORD = (8, "记录已存在!")
    NOT_EXIST_RECORD = (9, "记录不存在!")
    INVALID_CREDENTIALS = (10, "无效凭证!")
    TOKEN_EXPIRED = (11, "令牌已过期!")
    INVALID_TOKEN = (12, "无效令牌!")
    NO_PERMISSION_TO_ACCESS = (519, "无访问权限!")

    def __new__(cls, code, message):
        obj = object.__new__(cls)
        obj._value_ = code
        obj.message = message
        return obj

    @classmethod
    def get_message(cls, code) -> str:
        for api_code in cls:
            if api_code.value == code.value:
                return api_code.message
        return "未知错误代码"


if __name__ == "__main__":
    # 使用
    errorcode = ApiCode.INVALID_PARAMETER
    message = ApiCode.get_message(errorcode.value)
    print(message)  # 输出: 无效参数!
