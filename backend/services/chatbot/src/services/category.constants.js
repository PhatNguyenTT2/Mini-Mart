/**
 * Category Constants — Comprehensive mapping between user intent keywords and DB categories.
 * Derived from all 173 categories in seed-1000.sql (BHX catalog structure).
 */
const CATEGORY_KEYWORD_MAP = {
  // Fresh Foods (Thịt, cá, trứng, hải sản)
  'thịt heo': ['Thịt heo', 'Xúc xích, lạp xưởng, giò chả'],
  'thịt bò': ['Thịt bò'],
  'thịt gà': ['Thịt gà, vịt'],
  'thịt vịt': ['Thịt gà, vịt'],
  'cá': ['Cá, hải sản', 'Cá hộp', 'Cá mắm, dưa mắm'],
  'hải sản': ['Cá, hải sản', 'Thủy hải sản, thịt đông'],
  'tôm': ['Cá, hải sản'],
  'mực': ['Cá, hải sản'],
  'trứng': ['Trứng gà, vịt, cút'],

  // Produce (Rau, củ, nấm, trái cây)
  'rau': ['Rau lá', 'Rau củ', 'Rau, củ, nấm, trái cây'],
  'củ': ['Củ, quả'],
  'quả': ['Củ, quả', 'Trái cây'],
  'trái cây': ['Trái cây', 'Trái cây sấy'],
  'nấm': ['Nấm các loại', 'Đậu, nấm, đồ khô'],
  'hoa': ['Hoa tươi'],

  // Seasonings & Oils (Dầu ăn, nước chấm, gia vị)
  'dầu ăn': ['Dầu ăn', 'Dầu hào, giấm, bơ'],
  'nước mắm': ['Nước mắm', 'Nước chấm, mắm'],
  'nước tương': ['Nước tương'],
  'đường': ['Đường'],
  'hạt nêm': ['Hạt nêm, bột ngọt, bột canh'],
  'bột ngọt': ['Hạt nêm, bột ngọt, bột canh'],
  'muối': ['Muối'],
  'tương ớt': ['Tương ớt - đen, mayonnaise'],
  'tương đen': ['Tương ớt - đen, mayonnaise'],
  'mayonnaise': ['Tương ớt - đen, mayonnaise'],
  'dầu hào': ['Dầu hào, giấm, bơ'],
  'giấm': ['Dầu hào, giấm, bơ'],
  'bơ': ['Dầu hào, giấm, bơ'],
  'gia vị': ['Gia vị nêm sẵn', 'Dầu ăn, nước chấm, gia vị', 'Bột nghệ, tỏi, hồi, quế,...', 'Gia vị tẩm ướp'],
  'tiêu': ['Tiêu, sa tế, ớt bột'],
  'sa tế': ['Tiêu, sa tế, ớt bột'],
  'ớt bột': ['Tiêu, sa tế, ớt bột'],

  // Staples & Dry Goods (Gạo, bột, đồ khô)
  'gạo': ['Gạo, nếp các loại'],
  'nếp': ['Gạo, nếp các loại'],
  'xúc xích': ['Xúc xích', 'Xúc xích, lạp xưởng, giò chả'],
  'cá hộp': ['Cá hộp'],
  'thịt hộp': ['Heo, bò, pate hộp'],
  'pate': ['Heo, bò, pate hộp'],
  'đồ chay': ['Mì, hủ tiếu chay', 'Đồ chay các loại'],
  'chao': ['Chao'],
  'bột': ['Bột các loại'],
  'đậu khô': ['Đậu, nấm, đồ khô'],
  'rong biển': ['Rong biển các loại'],
  'bánh phồng': ['Bánh phồng, bánh đa'],
  'bánh tráng': ['Bánh tráng các loại', 'Cơm cháy, bánh tráng'],
  'nước cốt dừa': ['Nước cốt dừa lon'],

  // Instant Noodles, Porridge, Pasta (Mì, miến, cháo, phở)
  'mì': ['Mì ăn liền', 'Mì Ý, mì trứng'],
  'mì ăn liền': ['Mì ăn liền'],
  'hủ tiếu': ['Hủ tiếu, miến', 'Miến, hủ tiếu, phở khô'],
  'miến': ['Hủ tiếu, miến', 'Miến, hủ tiếu, phở khô'],
  'phở': ['Phở, bún ăn liền', 'Miến, hủ tiếu, phở khô'],
  'bún': ['Bún các loại', 'Phở, bún ăn liền'],
  'cháo': ['Cháo gói, cháo tươi'],
  'nui': ['Nui các loại'],
  'tokbokki': ['Bánh gạo Hàn Quốc'],
  'bánh gạo tokbokki': ['Bánh gạo Hàn Quốc'],
  'spaghetti': ['Mì Ý, mì trứng'],

  // Dairy & Ice Cream (Sữa các loại, Kem, sữa chua)
  'sữa': ['Sữa tươi', 'Sữa chua', 'Sữa chua uống liền', 'Sữa bột, pha sẵn', 'Sữa hạt, sữa đậu', 'Sữa các loại'],
  'sữa tươi': ['Sữa tươi'],
  'sữa chua': ['Sữa chua', 'Sữa chua uống liền'],
  'sữa đặc': ['Sữa đặc'],
  'ngũ cốc': ['Ngũ cốc', 'Ngũ cốc, yến mạch'],
  'kem': ['Kem'],

  // Frozen Foods (Thực phẩm đông mát)
  'đông lạnh': ['Hàng đông chế biến', 'Thủy hải sản, thịt đông', 'Viên đông, viên mát'],
  'chả giò': ['Chả giò'],

  // Beverages & Alcohol (Bia, nước giải khát, Cà phê, Trà)
  'bia': ['Bia', 'Bia, nước có cồn', 'Bia, nước giải khát'],
  'rượu': ['Rượu'],
  'nước suối': ['Nước suối'],
  'nước khoáng': ['Nước suối'],
  'nước ngọt': ['Nước ngọt', 'Nước ngọt có ga', 'Bia, nước giải khát'],
  'coca': ['Nước ngọt'],
  'pepsi': ['Nước ngọt'],
  'nước tăng lực': ['Nước tăng lực, bù khoáng'],
  'sting': ['Nước tăng lực, bù khoáng'],
  'nước yến': ['Nước yến'],
  'nước ép': ['Nước ép trái cây'],
  'sữa trái cây': ['Sữa trái cây'],
  'cà phê': ['Cà phê lon', 'Cà phê hoà tan', 'Cà phê pha phin'],
  'trà': ['Nước trà', 'Trà khô, túi lọc'],
  'mật ong': ['Mật ong'],

  // Snacks & Confectionery (Bánh kẹo các loại)
  'bánh': ['Bánh quy', 'Bánh snack', 'Bánh gạo', 'Bánh xốp', 'Bánh tươi, Sandwich', 'Bánh bông lan', 'Bánh Chocopie', 'Bánh kẹo các loại'],
  'bánh quy': ['Bánh quy'],
  'bánh mì': ['Bánh tươi, Sandwich'],
  'sandwich': ['Bánh tươi, Sandwich'],
  'snack': ['Bánh snack', 'Ăn vặt các loại', 'Khô chế biến sẵn', 'Snack & Đồ nhắm'],
  'bim bim': ['Bánh snack', 'Ăn vặt các loại', 'Snack & Đồ nhắm'],
  'kẹo': ['Kẹo cứng', 'Kẹo dẻo, kẹo marshmallow', 'Kẹo singum'],
  'khô bò': ['Khô chế biến sẵn'],
  'khô gà': ['Khô chế biến sẵn'],
  'khô heo': ['Khô chế biến sẵn'],
  'hạt': ['Hạt khô'],
  'đồ ăn vặt': ['Bánh snack', 'Khô chế biến sẵn', 'Hạt khô', 'Ăn vặt các loại'],
  'ăn vặt': ['Bánh snack', 'Khô chế biến sẵn', 'Hạt khô', 'Ăn vặt các loại'],
  'socola': ['Socola'],

  // Personal Care (Chăm sóc cá nhân)
  'dầu gội': ['Dầu gội'],
  'dầu xả': ['Dầu xả, kem ủ'],
  'sữa tắm': ['Sữa tắm'],
  'kem đánh răng': ['Kem đánh răng'],
  'bàn chải': ['Bàn chải, tăm chỉ nha khoa', 'Bàn chải'],
  'nước súc miệng': ['Nước súc miệng'],
  'xà bông': ['Xà bông cục', 'Nước rửa tay'],
  'giấy vệ sinh': ['Giấy vệ sinh', 'Khăn giấy'],
  'khăn ướt': ['Khăn ướt'],
  'tẩy trang': ['Tẩy trang'],
  'kem chống nắng': ['Kem chống nắng'],

  // Household & Cleaning (Vệ sinh nhà cửa & Đồ dùng gia đình)
  'nước giặt': ['Nước giặt'],
  'bột giặt': ['Bột giặt'],
  'nước xả vải': ['Nước xả'],
  'nước rửa chén': ['Nước rửa chén'],
  'nước lau nhà': ['Nước lau nhà'],
  'túi rác': ['Túi đựng rác'],
  'pin': ['Pin tiểu'],
  'chảo': ['Chảo'],
  'dao': ['Dao, kéo', 'Dao, bọt cạo râu']
};

/**
 * Persona-Preferred Categories mapping for candidate generation fallback.
 * Aligned with the canonical benchmark-spec-v4.json persona definitions:
 * - 0: Nội Trợ (Thịt, rau, gia vị, trứng, dầu ăn)
 * - 1: Sinh Viên (Mì, bánh snack, nước ngọt, ăn vặt)
 * - 2: Dân Nhậu (Bia, rượu, snack & đồ nhắm, khô chế biến)
 * - 3: Vãng Lai (Sản phẩm bán chạy nhất / popular bestsellers across top categories)
 */
const PERSONA_PREFERRED_CATEGORIES = {
  0: ['Thịt heo', 'Rau lá', 'Gia vị nêm sẵn', 'Dầu ăn', 'Nước mắm', 'Trứng gà, vịt, cút', 'Củ, quả', 'Rau, củ, nấm, trái cây'],
  1: ['Mì ăn liền', 'Bánh snack', 'Nước ngọt', 'Cháo gói, cháo tươi', 'Bún các loại', 'Ăn vặt các loại', 'Nước tăng lực, bù khoáng'],
  2: ['Bia', 'Rượu', 'Snack & Đồ nhắm', 'Bia, nước giải khát', 'Bánh snack', 'Khô chế biến sẵn', 'Hạt khô', 'Ăn vặt các loại'],
  3: ['Bia', 'Mì ăn liền', 'Nước ngọt', 'Bánh snack', 'Sữa tươi', 'Gia vị nêm sẵn']
};

module.exports = {
  CATEGORY_KEYWORD_MAP,
  PERSONA_PREFERRED_CATEGORIES
};

