# TravelBuddy Agent 🌍✈️

TravelBuddy là một mô hình trợ lý ảo AI đóng vai trò như một chuyên viên tư vấn du lịch thông minh, giúp bạn trả lời và xử lý các yêu cầu như:

- Tìm kiếm giá vé máy bay các chặng nội địa nội địa của Việt Nam (Vietnam Airlines, VietJet, Bamboo Airways).
- Gợi ý khách sạn theo địa điểm, xếp hạng (số sao) và theo mức ngân sách.
- Tính toán & hạch toán tài chính, cảnh báo cho người dùng khi chuyến đi có thể vượt quá ngân sách.
- Hỗ trợ trò chuyện tương tác tự nhiên, luôn xác minh lại thông tin thiếu trước khi cung cấp giải pháp.
- Bảo vệ Guardrail, từ chối mọi yêu cầu ngoại lệ như làm bài tập lập trình hay tư vấn các lĩnh vực không liên quan.

## Tổng quan Kiến trúc

Dự án áp dụng khung kiến trúc Agentic thông thường sử dụng **LangGraph** & **LangChain** để quản lý trạng thái máy chọn (StateGraph) giúp điều hướng cuộc hội thoại và sử dụng công cụ:

- `agent.py`: File lõi, thiết lập LangChain Node và ToolsNode. Liên kết API (`ChatOpenAI` kết nối qua Azure AI hoặc OpenAI), gắn System Prompt và vận hành qua cửa sổ Terminal.
- `tools.py`: Data Mock và logic chứa tập Tool `@tool` mà LLM sẽ gọi: `search_flights`, `search_hotels`, `calculate_budget`. Toàn bộ Tool được xử lý với `Try-Except` tránh crash hệ thống và trả về hướng dẫn an toàn cho người dùng.
- `system_prompt.txt`: Được viết bằng Tiếng Việt. Đóng vai trò là hiến pháp cho Mô hình, yêu cầu gọi Tool thay vì bịa kết quả.
- `test_agent.py` & `test_result.md`: Hệ thống kiểm thử 7 Tests mô phỏng các Case giả định để đánh giá độ chính xác của AI.

## Cài đặt Môi trường

1. Yêu cầu có Python 3.10+
2. Tạo Virtual Environment và cài đặt gói thư viện (các thư viện liên quan như Langchain, Dotenv).

```sh
python -m venv venv
.\venv\Scripts\activate    # trên Windows
pip install -r requirements.txt # (nếu có, hoặc tự install langchain_openai, langgraph, python-dotenv)
```

3. Cấu hình xác thực `.env`:
   Tạo `.`env` file cung cấp API authentication tokens hỗ trợ một trong hai tuỳ chọn:

```env
GITHUB_PAT=ghp_xyz...       # Để dùng Azure Models Inference
OPENAI_API_KEY=sk-xyz...    # Để dùng trực tiếp the OpenAI API
```

## Cách chạy

Khởi động tương tác trên Terminal bằng script gốc:

```sh
python agent.py
```

> _Gõ `quit`, `exit`, hoặc `q` để thoát chương trình._

## Testing (Kiểm thử)

Project có bộ Unit Chat test bằng script riêng, xuất kết quả vào file Markdown:

```sh
python test_agent.py
```

> Kết quả mô tả 7 rules (Direct Chat, Single/Multi chaining tool v.v) sẽ được phân tích chi tiết log trong `test_result.md`.

---

_Developed for Learning & AI Agent Experiment._
