import requests
import time

url = "https://docs.google.com/forms/d/e/1FAIpQLSfEYmjpocofrUgUUMGSQyYfhg_tkcinbvaOA2vUYFeeEsCBug/formResponse"

data = {
    "entry.1474095192": "f. Cả 5 đáp án trên",
    "entry.1822584696": [
        "a. Vận động nhẹ nhàng",
        # "b. Ngủ đủ giấc"
    ],
    "entry.327559767": "c. Tính theo vòng kinh",
    "entry.594918209": "f. Tất cả các đáp án trên",
    "entry.1715847582": "b. Đường giao tiếp thông thường (ôm, hôn, bắt tay...)",
    "entry.142131545": "a. Sử dụng  bao cao su",
    "entry.1339329007": "c. Cả hai đap án trên",
    "entry.1594610636": "e. Tất cả các đáp án trên",
    "entry.72082104": "b. Do nhiễm virut HPV",
    "entry.1640844111": "e. Tất cả các đáp án trên"
}

count = 200  # số lần submit

for i in range(count):
    r = requests.post(url, data=data)
    print("Submitted", i + 1, "status:", r.status_code)
    time.sleep(1)