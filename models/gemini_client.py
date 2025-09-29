import google.generativeai as genai
from config import Config
from typing import Dict, List, Optional
import json

class GeminiClient:
    def __init__(self):
        genai.configure(api_key=Config.GEMINI_API_KEY)

        # Use gemini-flash-lite-latest as requested
        try:
            self.model = genai.GenerativeModel('gemini-flash-lite-latest')
            print("Successfully initialized with model: gemini-flash-lite-latest")
        except Exception as e:
            print(f"Failed to initialize gemini-flash-lite-latest: {e}")
            # Fallback to other models
            model_names = [
                'gemini-pro',
                'gemini-1.5-flash-latest',
                'gemini-1.5-flash',
                'gemini-1.5-flash-001'
            ]

            self.model = None
            for model_name in model_names:
                try:
                    self.model = genai.GenerativeModel(model_name)
                    print(f"Successfully initialized with fallback model: {model_name}")
                    break
                except Exception as fallback_error:
                    print(f"Failed to initialize model {model_name}: {fallback_error}")
                    continue

            if self.model is None:
                raise Exception("Could not initialize any Gemini model")

        self.conversation_history: List[Dict] = []

    def generate_response(self, user_message: str, context_data: Optional[Dict] = None) -> str:
        """
        Generate AI response using Gemini 1.5 Flash with optional context data
        """
        try:
            # Build the prompt with context
            prompt = self._build_prompt(user_message, context_data)

            # Generate response
            response = self.model.generate_content(prompt)

            # Store conversation history
            self._update_conversation_history(user_message, response.text)

            return response.text

        except Exception as e:
            return f"Xin lỗi, đã có lỗi xảy ra khi xử lý yêu cầu của bạn: {str(e)}"

    def _build_prompt(self, user_message: str, context_data: Optional[Dict] = None) -> str:
        """
        Build comprehensive prompt for AriX - Professional Investment Analyst
        """
        system_prompt = """Bạn là AriX - Cố vấn Phân tích Đầu tư Chuyên nghiệp của hệ thống IQX.

**ĐỊNH DANH & VAI TRÒ:**
- Tên: AriX (AI Investment Research & eXpert)
- Vai trò: Cố vấn phân tích đầu tư chuyên nghiệp
- Chuyên môn: Phân tích chứng khoán, định giá doanh nghiệp, tư vấn đầu tư

**PHONG CÁCH GIAO TIẾP:**
- Nghiêm túc, chuyên nghiệp như chuyên gia trong công ty chứng khoán
- Chuẩn mực, ngắn gọn, đi thẳng vào vấn đề
- Luôn có số liệu dẫn chứng cụ thể
- Hạn chế cảm xúc cá nhân, tập trung vào phân tích khách quan
- Xưng hô: "AriX đánh giá...", "Theo phân tích của AriX...", "AriX khuyến nghị..."

**NGUYÊN TẮC TRẢ LỜI:**
1. **Số liệu là cốt lõi**: Luôn dẫn chứng số liệu cụ thể (giá, tỷ lệ, thời gian)
2. **Phân tích có căn cứ**: Giải thích logic đằng sau mỗi nhận định
3. **Khách quan tuyệt đối**: Không thiên vị, đưa ra cả ưu và nhược điểm
4. **Ngắn gọn hiệu quả**: Thông tin cốt lõi trong 2-3 đoạn ngắn
5. **Định hướng hành động**: Luôn kết thúc bằng khuyến nghị cụ thể

**FORMAT PHẢN HỒI (Markdown):**
```
### 📊 `MÃ CỔ PHIẾU` - Tên Công ty

**Giá hiện tại:** [số] VND (**[+/-]%** 📈📉)

**Đánh giá từ AriX:**
- ✅ **Khuyến nghị:** [Mua/Nắm giữ/Bán]
- 📊 **Định giá mục tiêu:** [số] VND
- 🔍 **Risk-Reward:** [Thấp/Trung bình/Cao]

**Căn cứ phân tích:**
1. [Lý do 1 với số liệu]
2. [Lý do 2 với số liệu]
3. [Lý do 3 với số liệu]

> ⚠️ **Lưu ý:** Đầu tư có rủi ro. Quyết định cuối cùng thuộc về nhà đầu tư.
```

**VÍ DỤ PHONG CÁCH:**
❌ Tránh: "VCB là cổ phiếu tuyệt vời, tôi nghĩ bạn nên mua!"
✅ Đúng: "AriX đánh giá VCB ở mức Khuyến nghị MUA với mục tiêu 95.000 VND (+8.2%) dựa trên P/E forward 11.2x, ROE 18.5% và tăng trưởng tín dụng 12%."

**LĨNH VỰC CHUYÊN MÔN:**
- Phân tích cơ bản (Fundamental Analysis)
- Định giá theo P/E, P/B, DCF, EV/EBITDA
- Phân tích báo cáo tài chính
- Đánh giá rủi ro và cơ hội
- Khuyến nghị đầu tư với mục tiêu giá cụ thể

Luôn nhớ: AriX là chuyên gia phân tích khách quan, không phải salesman."""

        # Add context data if available
        context_section = ""
        if context_data:
            context_section = f"\n\n**DỮ LIỆU THAM KHẢO:**\n```json\n{json.dumps(context_data, ensure_ascii=False, indent=2)}\n```"

        # Add conversation history
        history_section = ""
        if self.conversation_history:
            history_section = "\n\n**LỊCH SỬ HỘI THOẠI GÁN ĐÂY:**\n"
            for item in self.conversation_history[-2:]:  # Last 2 exchanges
                history_section += f"👤 **User:** {item['user']}\n🤖 **AriX:** {item['ai']}\n\n"

        full_prompt = f"{system_prompt}{context_section}{history_section}\n\n**CÂU HỎI HIỆN TẠI:** {user_message}\n\n**YÊU CẦU:** Trả lời bằng Markdown theo phong cách AriX chuyên nghiệp, có số liệu dẫn chứng."

        return full_prompt

    def _update_conversation_history(self, user_message: str, ai_response: str):
        """
        Update conversation history with size limit
        """
        self.conversation_history.append({
            'user': user_message,
            'ai': ai_response
        })

        # Keep only recent conversations
        if len(self.conversation_history) > Config.MAX_CONVERSATION_HISTORY:
            self.conversation_history = self.conversation_history[-Config.MAX_CONVERSATION_HISTORY:]

    def clear_history(self):
        """
        Clear conversation history
        """
        self.conversation_history = []

    def analyze_stock_data(self, stock_symbol: str, data: Dict) -> str:
        """
        Specialized method for stock data analysis
        """
        analysis_prompt = f"""
        Hãy phân tích dữ liệu cổ phiếu {stock_symbol} sau đây và đưa ra nhận xét về:
        1. Xu hướng giá
        2. Khối lượng giao dịch
        3. Các chỉ số tài chính quan trọng
        4. Đánh giá tổng quan và khuyến nghị (nếu có đủ thông tin)

        Dữ liệu: {json.dumps(data, ensure_ascii=False, indent=2)}
        """

        try:
            response = self.model.generate_content(analysis_prompt)
            return response.text
        except Exception as e:
            return f"Không thể phân tích dữ liệu: {str(e)}"