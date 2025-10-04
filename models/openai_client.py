import requests
from config import Config
from typing import Dict, List, Optional
import json

class OpenAIClient:
    def __init__(self):
        self.api_key = Config.OPENAI_API_KEY
        self.api_url = "https://v98store.com/v1/chat/completions"
        
        # Model configuration - using GPT-4 Turbo for best results
        self.model = "gpt-4o-mini"
        self.temperature = 0.7
        self.max_tokens = 4096
        
        self.conversation_history: List[Dict] = []

    def _call_openai_api(self, messages: List[Dict], temperature: float = None, max_tokens: int = None) -> str:
        """
        Call OpenAI API directly using requests
        """
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature or self.temperature,
            "max_tokens": max_tokens or self.max_tokens
        }
        
        try:
            response = requests.post(
                self.api_url,
                headers=headers,
                json=payload,
                timeout=60
            )
            response.raise_for_status()
            
            result = response.json()
            return result['choices'][0]['message']['content']
            
        except requests.exceptions.RequestException as e:
            raise Exception(f"OpenAI API request failed: {str(e)}")
        except (KeyError, IndexError) as e:
            raise Exception(f"Invalid API response format: {str(e)}")

    def generate_response(self, user_message: str, context_data: Optional[Dict] = None) -> str:
        """
        Generate comprehensive response using natural conversation style
        """
        try:
            # Use comprehensive prompt for natural conversation
            prompt = self._build_prompt(user_message, context_data)

            # Generate response using OpenAI Chat API
            messages = [
                {"role": "system", "content": self._get_system_prompt()},
                {"role": "user", "content": prompt}
            ]
            
            response_text = self._call_openai_api(messages)

            # Store conversation history
            self._update_conversation_history(user_message, response_text)

            return response_text

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
            news_prompt = f"""Bạn là AriX - AI Tin tức Chứng khoán. Trả lời về tin tức với format markdown đẹp mắt.

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

**YÊU CẦU FORMAT MARKDOWN:**

Hiển thị 5-8 tin tức nổi bật (hoặc tất cả nếu ít hơn), mỗi tin PHẢI tuân thủ format markdown chuẩn sau:

### [Tiêu đề tin]

Đánh giá: <sentiment> (Tốt, Xấu, Trung lập)

[Đọc chi tiết →](/tin-tuc/<slug>)

---

**Sentiment mapping:**
- positive → "Tốt"
- negative → "Xấu"
- neutral → "Trung lập"

**Kết thúc với:**
💡 **Dữ liệu từ:** IQX

**LƯU Ý QUAN TRỌNG:**
- PHẢI có dòng trống giữa các phần để xuống dòng đúng
- Format phải giống y chang ví dụ trên
- PHẢI dùng markdown link: [Đọc chi tiết →](/tin-tuc/<slug>)
- KHÔNG dùng HTML tags như <a href="...">
- KHÔNG thêm tóm tắt hay nội dung gì thêm
- Lấy slug từ field "slug" trong data
- KHÔNG bịa thông tin, chỉ dùng dữ liệu có sẵn
"""

            messages = [
                {"role": "system", "content": "You are AriX - AI Stock News Assistant"},
                {"role": "user", "content": news_prompt}
            ]
            
            response_text = self._call_openai_api(messages)

            # Store conversation history
            self._update_conversation_history(user_message, response_text)

            return response_text

        except Exception as e:
            return f"Không thể lấy tin tức: {str(e)}"

    def _get_system_prompt(self) -> str:
        """
        Get system prompt for AriX
        """
        return """Bạn là AriX - Cố vấn Phân tích Đầu tư Chuyên nghiệp của hệ thống IQX.

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
1. **Nhất quán và đầy đủ**: Luôn trả lời theo cùng một format cố định cho cùng loại câu hỏi
2. **Thông tin cốt lõi**: Cung cấp đầy đủ dữ liệu quan trọng, đặc biệt là số liệu giá cổ phiếu
3. **Không phân tích dài dòng**: Tránh giải thích phức tạp hay phân tích sâu
4. **Không khuyến nghị**: Không đưa ra lời khuyên mua/bán hay định hướng đầu tư
5. **Trả lời trực tiếp**: Đi thẳng vào vấn đề, không lòng vòng

**FORMAT PHẢN HỒI CỐ ĐỊNH CHO CÂU HỎI VỀ GIÁ:**
Khi được hỏi về giá cổ phiếu (VD: "giá FPT", "FPT bao nhiêu"), BẮT BUỘC trả lời theo format sau:

Giá cổ phiếu [MÃ] hiện tại là [giá đóng cửa].

Chi tiết phiên giao dịch gần nhất:
- Giá mở cửa: [giá mở cửa]
- Giá đóng cửa: [giá đóng cửa]
- [Tăng/Giảm] [số điểm] ([phần trăm]%) so với phiên trước
- Khối lượng giao dịch: [khối lượng] cổ phiếu

**FORMAT PHẢN HỒI CHO CÂU HỎI KHÁC:**
Đối với câu hỏi không phải về giá, trả lời ngắn gọn:
VD: "VCB là ngân hàng lớn nhất. Cổ đông chính là SBV (74.8%). Biến động 1 năm -27.9%."

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

**VÍ DỤ CỤ THỂ:**

❌ Tránh (không nhất quán): "Giá cổ phiếu FPT đóng cửa ở mức 93.000. Mức giá này giảm 2.5 điểm, tương đương 2.62% so với phiên giao dịch trước."

✅ Đúng (nhất quán, đầy đủ):
"Giá cổ phiếu FPT hiện tại là 93.0.

Chi tiết phiên giao dịch gần nhất:
- Giá mở cửa: 95.500
- Giá đóng cửa: 93.000
- Giảm 2.5 điểm (-2.62%) so với phiên trước
- Khối lượng giao dịch: 12,018,800 cổ phiếu"

✅ Câu hỏi về công ty: "VCB thuộc ngành ngân hàng, niêm yết trên HOSE. Cổ đông lớn là Ngân hàng Nhà nước (74.8%) và Mizuho Bank (15%)."

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

**FORMAT KẾT QUẢ TRẢ VỀ:**
- Trả lời có dạng markdown, dễ đọc, dễ format nội dung trong khung chat

Luôn nhớ: Chỉ được phép trả lời đúng điều được hỏi, không được bịa đặt thông tin."""

    def _build_prompt(self, user_message: str, context_data: Optional[Dict] = None) -> str:
        """
        Build comprehensive prompt for AriX - Professional Investment Analyst
        """
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

        full_prompt = f"{context_section}{history_section}\n\n**CÂU HỎI HIỆN TẠI:** {user_message}\n\n**YÊU CẦU:** Trả lời bằng Markdown theo phong cách AriX chuyên nghiệp, có số liệu dẫn chứng."

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

            messages = [
                {"role": "system", "content": "You are a data extraction assistant"},
                {"role": "user", "content": data_prompt}
            ]
            
            return self._call_openai_api(messages, temperature=0.3, max_tokens=500)
            
        except Exception as e:
            return f"Không thể trích xuất dữ liệu: {str(e)}"
