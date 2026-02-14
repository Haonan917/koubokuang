import random
import time


def base36encode(number, alphabet='0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ'):
    """Converts an integer to a base36 string."""
    if not isinstance(number, int):
        raise TypeError('number must be an integer')

    base36 = ''
    sign = ''

    if number < 0:
        sign = '-'
        number = -number

    if 0 <= number < len(alphabet):
        return sign + alphabet[number]

    while number != 0:
        number, i = divmod(number, len(alphabet))
        base36 = alphabet[i] + base36

    return sign + base36


def base36decode(number):
    return int(number, 36)


def get_search_id():
    e = int(time.time() * 1000) << 64
    t = int(random.uniform(0, 2147483646))
    return base36encode((e + t))


img_cdns = [
    "https://sns-img-qc.xhscdn.com",
    "https://sns-img-hw.xhscdn.com",
    "https://sns-img-bd.xhscdn.com",
    "https://sns-img-qn.xhscdn.com",
]


def get_img_url_by_trace_id(trace_id: str, format_type: str = "png"):
    return f"{random.choice(img_cdns)}/{trace_id}?imageView2/format/{format_type}"


def get_img_urls_by_trace_id(trace_id: str, format_type: str = "png"):
    return [f"{cdn}/{trace_id}?imageView2/format/{format_type}" for cdn in img_cdns]


def get_trace_id(img_url: str):
    # 浏览器端上传的图片多了 /spectrum/ 这个路径
    return f"spectrum/{img_url.split('/')[-1]}" if img_url.find("spectrum") != -1 else img_url.split("/")[-1]


if __name__ == '__main__':
    _img_url = "https://sns-img-bd.xhscdn.com/7a3abfaf-90c1-a828-5de7-022c80b92aa3"
    # 获取一个图片地址在多个cdn下的url地址
    # final_img_urls = get_img_urls_by_trace_id(get_trace_id(_img_url))
    final_img_url = get_img_url_by_trace_id(get_trace_id(_img_url))
    print(final_img_url)
