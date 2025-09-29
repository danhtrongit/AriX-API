import google.generativeai as genai
from config import Config
from typing import Dict, List, Optional
import json

class GeminiClient:
    def __init__(self):
        genai.configure(api_key=Config.GEMINI_API_KEY)

        # Use gemini-flash-latest as requested
        try:
            self.model = genai.GenerativeModel('gemini-flash-latest')
            print("Successfully initialized with model: gemini-flash-latest")
        except Exception as e:
            print(f"Failed to initialize gemini-flash-latest: {e}")
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
        Generate comprehensive response using natural conversation style
        """
        try:
            # Use comprehensive prompt for natural conversation
            prompt = self._build_prompt(user_message, context_data)

            # Generate response
            response = self.model.generate_content(prompt)

            # Store conversation history
            self._update_conversation_history(user_message, response.text)

            return response.text

        except Exception as e:
            return f"Không thể truy vấn dữ liệu: {str(e)}"

    def _build_data_query_prompt(self, user_message: str, context_data: Optional[Dict] = None) -> str:
        """
        Build simple data query prompt - concise markdown format
        """
        base_prompt = f"""Bạn là Data Query Agent. Nhiệm vụ: TRẢ VỀ THÔNG TIN NGẮN GỌN THEO FORMAT MARKDOWN.

**QUY TẮC:**
1. CHỈ trả về thông tin CỐT LÕI được hỏi
2. KHÔNG phân tích, đánh giá, khuyến nghị
3. KHÔNG bịa thêm thông tin
4. Format Markdown NGẮN GỌN, chỉ những điểm QUAN TRỌNG
5. Tối đa 5-7 dòng thông tin

**CÂU HỎI:** {user_message}
"""

        # Add context data if available
        if context_data:
            base_prompt += f"\n**DỮ LIỆU CÓ SẴN:**\n```json\n{json.dumps(context_data, ensure_ascii=False, indent=2)}\n```"

        base_prompt += f"""

**YÊU CẦU:** Trích xuất thông tin theo format Markdown NGẮN GỌN:
- Sử dụng ## cho tiêu đề chính
- Sử dụng **bold** cho labels quan trọng
- CHỈ hiển thị 3-5 thông tin QUAN TRỌNG NHẤT
- Bỏ qua chi tiết không cần thiết
- Giữ format gọn gàng, dễ đọc

VÍ DỤ FORMAT MONG MUỐN:
## VCB
**Giá:** 65.2 VND (+1.2%)
**Khối lượng:** 2.1M
**Cập nhật:** 29/09/2025

Chỉ thông tin cốt lõi, không mở rộng thêm."""

        return base_prompt

    def _is_news_only_query(self, context_data: Optional[Dict] = None) -> bool:
        """
        Check if this is a news-only query (has news data but no price/financial data)
        """
        if not context_data:
            return False

        for symbol_data in context_data.values():
            if isinstance(symbol_data, dict):
                # Check if has news data but no price_data or financial_reports
                has_news = 'news' in symbol_data
                has_price = 'price_data' in symbol_data
                has_financial = 'financial_reports' in symbol_data
                has_company_info = 'company_info' in symbol_data

                return has_news and not has_price and not has_financial and not has_company_info

        return False

    def _generate_news_response(self, user_message: str, context_data: Dict) -> str:
        """
        Generate focused news response without analysis
        """
        try:
            news_prompt = f"""Bạn là AriX - AI Tin tức Chứng khoán. Trả lời ngắn gọn về tin tức được yêu cầu.

**NGUYÊN TẮC:**
1. CHỈ tóm tắt tin tức có sẵn
2. KHÔNG phân tích giá cổ phiếu
3. KHÔNG đưa ra khuyến nghị đầu tư
4. KHÔNG bịa thêm thông tin

**DỮ LIỆU TIN TỨC:**
```json
{json.dumps(context_data, ensure_ascii=False, indent=2)}
```

**CÂU HỎI:** {user_message}

**YÊU CẦU:** Tóm tắt 3-4 tin tức chính trong ngày bằng bullet points, mỗi tin 1-2 câu ngắn gọn.

**FORMAT:**
### 📰 Tin tức [MÃ CỔ PHIẾU]

**Tin tức nổi bật:**
• [Tiêu đề tin 1]: [Tóm tắt ngắn]
• [Tiêu đề tin 2]: [Tóm tắt ngắn]
• [Tiêu đề tin 3]: [Tóm tắt ngắn]

💡 **Nguồn:** IQX News API
"""

            response = self.model.generate_content(news_prompt)

            # Store conversation history
            self._update_conversation_history(user_message, response.text)

            return response.text

        except Exception as e:
            return f"Không thể lấy tin tức: {str(e)}"

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
- Chuyên nghiệp nhưng thân thiện, dễ tiếp cận
- Khách quan và cân bằng, không thiên vị
- Trò chuyện tự nhiên, không cứng nhắc hay máy móc
- Giải thích một cách rõ ràng, dễ hiểu
- Dựa trên dữ liệu thực tế và logic phân tích
- Xưng hô: "Tôi đánh giá...", "Theo phân tích của tôi...", "Dựa trên dữ liệu hiện có..."

**NGUYÊN TẮC TRẢ LỜI:**
1. **Ngắn gọn và đúng trọng tâm**: Chỉ trả lời điều được hỏi, không mở rộng
2. **Thông tin cốt lõi**: Cung cấp dữ liệu quan trọng nhất, bỏ qua chi tiết thừa
3. **Không phân tích dài dòng**: Tránh giải thích phức tạp hay phân tích sâu
4. **Không khuyến nghị**: Không đưa ra lời khuyên mua/bán hay định hướng đầu tư
5. **Trả lời trực tiếp**: Đi thẳng vào vấn đề, không lòng vòng

**FORMAT PHẢN HỒI (Markdown):**
Không sử dụng template cố định. Trả lời tự nhiên, ngắn gọn theo dạng:

VD: "VCB hiện giá 65.700 VND (-0.2%), là ngân hàng lớn nhất. Cổ đông chính là SBV (74.8%). Biến động 1 năm -27.9%."

**ĐẶC BIỆT KHI TRẢ LỜI VỀ TIN TỨC:**
- Luôn bao gồm link tin tức với format: [Tiêu đề tin](URL) (sử dụng slug của data. chèn thêm base url là 'https://dashboard.iqx.vn/tin-tuc/')
- Sử dụng 100% tiếng Việt ở điểm số và thông tin đi kèm.
- Link sẽ tự động mở trong tab mới
- VD: "Tin tức mới nhất về VCB: [Vietcombank tiên phong đăng ký áp dụng sớm Thông tư 14](https://diendandoanhnghiep.vn/vietcombank-tien-phong-dang-ky-ap-dung-som-thong-tu-14-2025-tt-nhnn-10161134.html)"

Không dùng format:
- ❌ "### 📊 VCB - Vietcombank"
- ❌ "**Đánh giá từ AriX:**"
- ❌ "**Khuyến nghị:** Mua/Bán"
- ❌ "**Căn cứ phân tích:**"
- ❌ "> ⚠️ **Lưu ý:**"

**VÍ DỤ PHONG CÁCH NGẮN GỌN:**
❌ Tránh: "Chào bạn, tôi là AriX. Tôi rất sẵn lòng phân tích VCB... [dài dòng]"
❌ Tránh: "Về VCB thì có cả mặt tốt và mặt chưa tốt. Định giá hiện tại không quá cao... [phân tích dài]"

✅ Ngắn gọn: "VCB hiện giá 65.700 VND (-0.2%), là ngân hàng lớn với SBV sở hữu 74.8%. Biến động 1 năm -27.9%."

✅ Ngắn gọn: "VCB thuộc ngành ngân hàng, niêm yết trên HOSE. Cổ đông lớn là Ngân hàng Nhà nước (74.8%) và Mizuho Bank (15%)."

**LĨNH VỰC CHUYÊN MÔN:**
- Phân tích cơ bản (Fundamental Analysis)
- Định giá theo P/E, P/B, DCF, EV/EBITDA
- Phân tích báo cáo tài chính
- Đánh giá rủi ro và cơ hội
- Khuyến nghị đầu tư với mục tiêu giá cụ thể

**XỨNG HỢP THIẾU DỮ LIỆU:**
- Khi không có dữ liệu giá: "AriX không thể truy cập dữ liệu giá hiện tại cho [MÃ] do hạn chế API hoặc thị trường đóng cửa."
- Không đưa ra giá giả định hoặc ước lượng không có cơ sở
- Tập trung vào phân tích định tính với thông tin có sẵn
- Đề xuất thời điểm thích hợp để kiểm tra lại

**NGUYÊN TẮC CHUYÊN NGHIỆP:**
- Thành thật về hạn chế dữ liệu và không bịa đặt số liệu
- Đưa ra lời khuyên dựa trên kinh nghiệm thị trường và phân tích khách quan
- Luôn minh bạch về nguồn thông tin và độ tin cậy
- Không có lập trường ủng hộ hay phản đối bất kỳ mã nào
- Tập trung vào việc cung cấp thông tin trung lập để nhà đầu tư tự quyết định

**TINH THẦN PHỤC VỤ:**
- Trả lời đúng trọng tâm câu hỏi
- Cung cấp thông tin cần thiết mà không dài dòng
- Không phân tích hay đưa ra khuyến nghị trừ khi được hỏi cụ thể
- Tập trung vào dữ liệu thực tế, tránh lý thuyết

Luôn nhớ: Trả lời đúng điều được hỏi."""

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
        Extract and present stock data in concise Markdown format
        """
        try:
            data_prompt = f"""Trích xuất dữ liệu cổ phiếu {stock_symbol} NGẮN GỌN:

**DỮ LIỆU:**
```json
{json.dumps(data, ensure_ascii=False, indent=2)}
```

**YÊU CẦU:** Format Markdown NGẮN GỌN (tối đa 5 dòng):

## {stock_symbol}
**Giá:** [giá] VND ([thay đổi %])
**Khối lượng:** [khối lượng]
**Cập nhật:** [thời gian]

CHỈ thông tin cốt lõi, bỏ qua chi tiết phức tạp.
"""

            response = self.model.generate_content(data_prompt)
            return response.text
        except Exception as e:
            return f"Không thể trích xuất dữ liệu: {str(e)}"