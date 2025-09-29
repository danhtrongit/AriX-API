# 🤖 AriX API - Phân tích viên độc lập

**AriX** là hệ thống phân tích đầu tư độc lập, cung cấp phân tích khách quan dựa trên dữ liệu cho thị trường chứng khoán Việt Nam.

## 🏢 Về AriX

**AriX** (AI Investment Research & eXpert) hoạt động như nhà phân tích độc lập, cung cấp:

- 📊 **Phân tích khách quan** dựa trên dữ liệu thực tế
- 📈 **Đánh giá đầu tư** có căn cứ rõ ràng
- 💰 **Định giá mục tiêu** dựa trên phân tích cơ bản
- 📰 **Phân tích tin tức** và tâm lý thị trường
- 🎯 **Đánh giá rủi ro** một cách cân bằng

## 🚀 Features

### Core Capabilities
- **Stock Price Analysis**: Real-time and historical price data
- **Financial Report Analysis**: P/E, ROE, ROA, and other key ratios
- **Investment Recommendations**: Buy/Hold/Sell with target prices
- **News Integration**: Latest market news with sentiment analysis
- **AI-Powered Insights**: Professional analysis using Google Gemini AI

### Technical Features
- **RESTful API** with comprehensive endpoints
- **Markdown Response Format** for rich formatting
- **Multi-language Support** (Vietnamese & English)
- **Rate Limiting** and error handling
- **Docker Support** for easy deployment
- **Professional Logging** and monitoring

## 📊 API Endpoints

### Chat Endpoint
```http
POST /api/chat
Content-Type: application/json

{
  "message": "Phân tích VCB hiện tại"
}
```

### Stock Data
```http
GET /api/stock/{symbol}?include_price=true&include_financial=true
```

### News Data
```http
GET /api/news/{symbol}?page_size=10&sentiment=positive
```

### Suggestions
```http
GET /api/suggestions
```

## 🐳 Docker Deployment

### Quick Start
```bash
# Clone the repository
git clone https://github.com/danhtrongit/AriX-API.git
cd AriX-API

# Copy environment configuration
cp .env.example .env
# Edit .env with your API keys

# Build and run with Docker Compose
docker-compose up --build -d

# Check status
docker-compose logs arix-api
```

### Environment Variables

```env
GEMINI_API_KEY=your_gemini_api_key_here
VNSTOCK_DEFAULT_SOURCE=VCI
FLASK_ENV=production
DEBUG=False
LOG_LEVEL=INFO
```

## 🔧 Manual Installation

### Prerequisites
- Python 3.11+
- pip package manager

### Installation Steps
```bash
# Clone repository
git clone https://github.com/danhtrongit/AriX-API.git
cd AriX-API

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env file with your configuration

# Run the application
python app.py
```

## 📈 Usage Examples

### Professional Stock Analysis
```python
import requests

# Get professional analysis
response = requests.post('http://localhost:5005/api/chat', json={
    'message': 'Đánh giá VCB với mục tiêu đầu tư 6 tháng'
})

print(response.json()['response'])
```

### Expected Response
```markdown
### 📊 `VCB` - Vietcombank

**Giá hiện tại:** 95.500 VND (**+1.2%** 📈)

**Đánh giá từ AriX:**
- ✅ **Khuyến nghị:** Mua
- 📊 **Định giá mục tiêu:** 105.000 VND
- 🔍 **Risk-Reward:** Thấp

**Căn cứ phân tích:**
1. ROE cao 18.5% vượt trung bình ngành
2. P/E forward 11.2x hấp dẫn
3. Tăng trưởng tín dụng ổn định 12%

> ⚠️ **Lưu ý:** Đầu tư có rủi ro. Quyết định cuối cùng thuộc về nhà đầu tư.
```

## 🏗️ Architecture

```
AriX API
├── models/
│   ├── gemini_client.py      # Google Gemini AI integration
│   ├── vnstock_client.py     # Vietnamese stock data
│   └── iqx_news_client.py    # News data integration
├── services/
│   ├── chat_service.py       # Main chat logic
│   ├── query_parser.py       # AI-powered query parsing
│   └── ai_symbol_detector.py # Smart symbol detection
├── utils/
│   ├── json_utils.py         # JSON serialization
│   ├── logger.py             # Logging configuration
│   └── validators.py         # Input/output validation
├── config.py                 # Configuration management
└── app.py                    # Flask application entry point
```
- **Xử lý lỗi robust**: Logging và validation toàn diện

## Cấu trúc dự án

```
backend/
├── app.py                 # Main Flask application
├── config.py             # Configuration settings
├── requirements.txt      # Python dependencies
├── .env                 # Environment variables
├── models/              # Data models
│   ├── gemini_client.py  # Gemini 1.5 Flash integration
│   └── vnstock_client.py # VNStock API integration
├── services/            # Business logic
│   ├── chat_service.py   # Main chatbot service
│   ├── data_service.py   # Data processing service
│   └── query_parser.py   # Natural language processing
├── utils/               # Utilities
│   ├── logger.py        # Logging configuration
│   └── validators.py    # Input validation
└── tests/              # Test suites
    └── test_main.py    # Main test file
```

## Cài đặt

1. **Clone repository và setup môi trường**:
```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

2. **Cấu hình environment variables**:
Chỉnh sửa file `.env`:
```
GEMINI_API_KEY=your-gemini-api-key-here
SECRET_KEY=your-flask-secret-key-here
DEBUG=True
VNSTOCK_DEFAULT_SOURCE=TCBS
MAX_CONVERSATION_HISTORY=10
LOG_LEVEL=INFO
```

3. **Chạy ứng dụng**:
```bash
python app.py
```

API sẽ chạy tại `http://localhost:5000`

## API Endpoints

### Chat
- `POST /api/chat` - Chat với AI agent
- `GET /api/chat/history` - Lấy lịch sử chat
- `POST /api/chat/clear` - Xóa lịch sử chat
- `GET /api/suggestions` - Lấy gợi ý câu hỏi

### Stock Data
- `GET /api/stock/{symbol}` - Thông tin chi tiết cổ phiếu
- `GET /api/stock/{symbol}/price` - Giá cổ phiếu
- `POST /api/stocks/compare` - So sánh nhiều cổ phiếu

### Market & Portfolio
- `GET /api/market/summary` - Tổng quan thị trường
- `POST /api/portfolio/analyze` - Phân tích danh mục

### Examples

**Chat với AI:**
```bash
curl -X POST http://localhost:5000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Giá cổ phiếu VCB hôm nay như thế nào?"}'
```

**Lấy thông tin cổ phiếu:**
```bash
curl http://localhost:5000/api/stock/VCB
```

**Lấy lịch sử giá:**
```bash
curl "http://localhost:5000/api/stock/VCB/price?start_date=2024-01-01&end_date=2024-01-31"
```

## Testing

Chạy tests:
```bash
pytest tests/ -v
```

## Các tính năng AI Agent

1. **Hiểu ngữ cảnh**: Phân tích câu hỏi để xác định:
   - Loại truy vấn (giá cổ phiếu, thông tin công ty, báo cáo tài chính)
   - Mã cổ phiếu
   - Khoảng thời gian
   - Ý định người dùng

2. **Truy vấn dữ liệu thông minh**: Tự động lấy dữ liệu cần thiết từ VNStock

3. **Phân tích và tư vấn**: Sử dụng Gemini 1.5 Flash để phân tích dữ liệu và đưa ra nhận xét

4. **Ghi nhớ ngữ cảnh**: Duy trì lịch sử hội thoại để câu trả lời có tính liên tục

## Tích hợp VNStock

Ứng dụng tích hợp đầy đủ với VNStock API bao gồm:

- **Thông tin công ty**: Overview, cổ đông, lãnh đạo, công ty con
- **Dữ liệu giá**: Giá lịch sử, giá hiện tại
- **Báo cáo tài chính**: BCTC, bảng cân đối kế toán, lưu chuyển tiền tệ
- **Thống kê thị trường**: Các chỉ số và xu hướng

## Bảo mật

- Input validation và sanitization
- Error handling toàn diện
- Logging chi tiết cho monitoring
- CORS configuration cho frontend integration

## Phát triển tiếp

- [ ] Thêm caching cho dữ liệu thường xuyên truy cập
- [ ] Implement WebSocket cho real-time updates
- [ ] Thêm authentication và authorization
- [ ] Tích hợp với nhiều data sources khác
- [ ] Phát triển dashboard frontend