# -*- coding: utf-8 -*-
"""
Bách Hóa Xanh Product Scraper

Collects real product metadata (name, unit_price, image_url, category_id)
from Bách Hóa Xanh web endpoints / search API to scale the product catalog to 5,000+ SKUs.

Output: backend/docs/chatbot/seed-product/raw_products_5000.json
"""

import urllib.request
import urllib.parse
import json
import time
import re
import os
from pathlib import Path

# Category list mapped to BHX search terms / category IDs
BHX_CATEGORIES = [
    {"id": 2, "name": "Thịt heo", "keywords": ["thịt heo", "ba rọi heo", "sườn heo", "chân giò heo", "thịt nạc heo"]},
    {"id": 3, "name": "Thịt bò", "keywords": ["thịt bò", "nạm bò", "đùi bò", "bắp bò", "bò xay", "ba chỉ bò"]},
    {"id": 4, "name": "Thịt gà, vịt", "keywords": ["thịt gà", "ức gà", "đùi gà", "cánh gà", "vịt", "gà nguyên con"]},
    {"id": 5, "name": "Cá, hải sản", "keywords": ["cá basa", "cá diêu hồng", "cá nục", "tôm tuơi", "mực tươi", "cá thu", "cá lóc", "cá chẽm", "cá hồi"]},
    {"id": 6, "name": "Trứng gà, vịt, cút", "keywords": ["trứng gà", "trứng vịt", "trứng cút", "trứng muối", "trứng bắc thảo"]},
    {"id": 8, "name": "Trái cây", "keywords": ["cam sành", "táo", "nho", "chuối", "lê", "quýt", "xoài", "dưa hấu", "bưởi", "sầu riêng", "bơ", "thơm", "ổi", "thanh long"]},
    {"id": 9, "name": "Rau lá", "keywords": ["rau mồng tơi", "cải bẹ xanh", "cải thìa", "rau muống", "cải ngọt", "rau lang", "xà lách", "rau dền", "cần tây", "rau ngót"]},
    {"id": 10, "name": "Củ, quả", "keywords": ["bắp mỹ", "bắp cải", "khoai tây", "bí đỏ", "cà chua", "cà rốt", "khoai lang", "dưa leo", "khổ qua", "bầu", "bí đao", "hành tây"]},
    {"id": 11, "name": "Nấm các loại", "keywords": ["nấm kim châm", "nấm hải sản", "nấm đùi gà", "nấm linh chi", "nấm hương", "nấm rơm", "nấm bao ngư", "nấm mỡ"]},
    {"id": 14, "name": "Dầu ăn", "keywords": ["dầu ăn", "dầu đậu nành", "dầu olive", "dầu mè", "dầu thực vật", "dầu hướng dương"]},
    {"id": 15, "name": "Nước mắm", "keywords": ["nước mắm", "nước mắm cá cơm", "nước mắm chinsu", "nước mắm nam ngư", "nước mắm khải hoàn"]},
    {"id": 16, "name": "Nước tương", "keywords": ["nước tương", "nước tương maggi", "nước tương tam thái tử", "nước tương chinsu", "nước tương nam dương"]},
    {"id": 17, "name": "Đường", "keywords": ["đường kính trắng", "đường mía", "đường phèn", "đường thốt nốt", "đường vàng"]},
    {"id": 18, "name": "Hạt nêm, bột ngọt", "keywords": ["hạt nêm", "hạt nêm knorr", "hạt nêm maggi", "bột ngọt", "bột ngọt ajinomoto", "hạt nêm aji-ngon"]},
    {"id": 19, "name": "Muối", "keywords": ["muối sấy", "muối tôm", "muối tiêu", "muối ớt tây ninh", "muối bọt"]},
    {"id": 20, "name": "Tương ớt - đen, mayonnaise", "keywords": ["tương ớt", "tương cà", "tương đen", "mayonnaise", "tương ớt chinsu", "tương ớt cholimex"]},
    {"id": 21, "name": "Dầu hào, giấm, bơ", "keywords": ["dầu hào", "giấm", "bơ thực vật", "bơ đậu phộng", "giấm táo"]},
    {"id": 22, "name": "Gia vị nêm sẵn", "keywords": ["gia vị kho cá", "gia vị thịt kho", "lẩu thái", "gia vị nấu phở", "xốt nướng"]},
    {"id": 23, "name": "Nước chấm, mắm", "keywords": ["muối ớt xanh", "mắm tôm", "mắm ruốc", "nước chấm mè rang", "xốt thái"]},
    {"id": 24, "name": "Tiêu, sa tế, ớt bột", "keywords": ["tiêu đen", "tiêu sọ", "ớt bột", "sa tế tôm", "ớt xay"]},
    {"id": 25, "name": "Bột nghệ, tỏi, hồi, quế", "keywords": ["bột nghệ", "bột tỏi", "bột ngũ vị hương", "nước màu", "hoa hồi", "quế cây"]},
    {"id": 27, "name": "Gạo, nếp các loại", "keywords": ["gạo st25", "gạo neptune", "gạo thơm lài", "gạo nở xốp", "gạo lứt", "nếp nương"]},
    {"id": 28, "name": "Xúc xích", "keywords": ["xúc xích", "xúc xích heo", "xúc xích bò", "xúc xích phô mai", "xúc xích cp", "xúc xích ponnie"]},
    {"id": 29, "name": "Cá hộp", "keywords": ["cá nục sốt cà", "cá mòi sốt cà", "cá ngừ ngâm dầu", "cá trích sốt cà"]},
    {"id": 30, "name": "Heo, bò, pate hộp", "keywords": ["thịt heo hộp", "pate gan", "heo hai lát", "bò hai lát", "spam"]},
    {"id": 31, "name": "Mì, hủ tiếu chay", "keywords": ["mì chay", "phở chay", "hủ tiếu chay", "cháo chay"]},
    {"id": 33, "name": "Đồ chay các loại", "keywords": ["đậu hũ", "đậu hũ non", "đậu hũ chiên", "sườn non chay", "bánh bao chay"]},
    {"id": 34, "name": "Bột các loại", "keywords": ["bột mì", "bột chiên giòn", "bột phô mai", "bột rau câu", "baking soda"]},
    {"id": 35, "name": "Đậu, nấm, đồ khô", "keywords": ["đậu nành", "đậu xanh", "mè đen", "nấm tuyết", "táo đỏ", "măng khô"]},
    {"id": 36, "name": "Rong biển các loại", "keywords": ["rong biển ăn liền", "rong biển rắc cơm", "rong biển cuộn", "rong nho"]},
    {"id": 38, "name": "Bánh phồng, bánh đa", "keywords": ["bánh phồng tôm", "bánh tráng nướng", "bánh phồng rau củ"]},
    {"id": 39, "name": "Bánh tráng các loại", "keywords": ["bánh tráng gạo", "bánh tráng siêu mỏng", "bánh tráng chả giò"]},
    {"id": 40, "name": "Nước cốt dừa lon", "keywords": ["nước cốt dừa", "bột cốt dừa"]},
    {"id": 42, "name": "Mì ăn liền", "keywords": ["mì hảo hảo", "mì gấu đỏ", "mì 3 miền", "mì kokomi", "mì cung đình", "mì omachi", "mì koreno", "mì shin", "mì khế"]},
    {"id": 43, "name": "Hủ tiếu, miến", "keywords": ["hủ tiếu vifon", "hủ tiếu nam vang", "bánh đa cua", "hủ tiếu sườn heo", "cơm tự sôi"]},
    {"id": 44, "name": "Phở, bún ăn liền", "keywords": ["phở bò vifon", "phở đệ nhất", "phở gà", "bún giò heo", "phở trộn"]},
    {"id": 45, "name": "Cháo gói, cháo tươi", "keywords": ["cháo tươi cây thị", "cháo tươi sg food", "cháo yến", "cháo vifon", "cháo sườn"]},
    {"id": 46, "name": "Bún các loại", "keywords": ["bún gạo mekong", "bún tươi", "bún lứt", "miến tươi", "bún khô"]},
    {"id": 47, "name": "Nui các loại", "keywords": ["nui trứng", "nui rau củ", "nui ống", "nui xoắn", "nui chữ c"]},
    {"id": 48, "name": "Miến, hủ tiếu, phở khô", "keywords": ["miến khoai lang", "phở khô", "miến dong", "bánh canh", "mì vắt"]},
    {"id": 49, "name": "Bánh gạo Hàn Quốc", "keywords": ["tokbokki", "tteokbokki", "yopokki"]},
    {"id": 50, "name": "Mì Ý, mì trứng", "keywords": ["mì spaghetti", "mì trứng safoco", "mì xào", "mì chùm ngây"]},
    {"id": 52, "name": "Sữa tươi", "keywords": ["sữa tươi vinamilk", "sữa tươi th true milk", "sữa tươi cô gái hà lan", "sữa tươi nutimilk", "sữa tươi kun", "sữa tươi milo"]},
    {"id": 53, "name": "Sữa chua uống liền", "keywords": ["sữa chua uống yomost", "sữa chua uống vinamilk", "sữa chua uống th true milk", "sữa chua uống probi", "sữa chua uống kun"]},
    {"id": 54, "name": "Sữa bột, pha sẵn", "keywords": ["sữa bột abbot", "sữa bột friso", "sữa bột enfa", "sữa bột anlene", "sữa tươi pha sẵn"]},
    {"id": 55, "name": "Sữa hạt, sữa đậu", "keywords": ["sữa đậu nành fami", "sữa hạt óc chó", "sữa hạnh nhân", "sữa hạt mầm"]},
    {"id": 56, "name": "Sữa đặc", "keywords": ["sữa đặc phương nam", "sữa đặc ngô sao phương nam", "sữa đặc ông thọ", "sữa đặc cô gái hà lan"]},
    {"id": 57, "name": "Ngũ cốc", "keywords": ["ngũ cốc dinh dưỡng", "bột ngũ cốc", "yến mạch", "granola"]},
    {"id": 58, "name": "Sữa chua", "keywords": ["sữa chua vinamilk", "sữa chua th true milk", "sữa chua nếp cẩm", "sữa chua nha đam"]},
    {"id": 60, "name": "Kem", "keywords": ["kem merino", "kem celano", "kem walls", "kem ốc quế", "kem hộp"]},
    {"id": 63, "name": "Xúc xích, lạp xưởng, giò chả", "keywords": ["lạp xưởng", "giò lụa", "chả lụa", "giò thủ", "xúc xích đức"]},
    {"id": 64, "name": "Hàng đông chế biến", "keywords": ["bánh xếp bibigo", "há cảo", "xíu mại", "pizza", "phô mai que"]},
    {"id": 65, "name": "Hàng mát chế biến", "keywords": ["đậu hũ cá phô mai", "chả cá", "thịt nguội"]},
    {"id": 66, "name": "Chả giò", "keywords": ["chả giò rế", "chả giò cầu tre", "chả giò hải sản", "chả ram"]},
    {"id": 67, "name": "Viên đông, viên mát", "keywords": ["cá viên", "bò viên", "tôm viên", "viên thả lẩu"]},
    {"id": 68, "name": "Thủy hải sản, thịt đông", "keywords": ["râu mực đông lạnh", "tôm đông lạnh", "cá hồi đông lạnh"]},
    {"id": 70, "name": "Nước suối", "keywords": ["nước khoáng lavie", "nước aquafina", "nước dasani", "nước vĩnh hảo", "nước ion alkaline"]},
    {"id": 71, "name": "Bia, nước có cồn", "keywords": ["bia heineken", "bia tiger", "bia saigon", "bia 333", "bia budweiser", "bia sapporo", "bia bia việt", "bia larue", "bia bia hơi", "bia stronghold", "bia hoegaarden"]},
    {"id": 72, "name": "Nước trà", "keywords": ["trà độ 0", "trà c2", "trà oolong tea+", "trà xanh ko độ", "trà thảo mộc dr thanh", "trà ô long"]},
    {"id": 73, "name": "Nước ngọt", "keywords": ["coca cola", "pepsi", "7up", "mirinda", "sprite", "fanta", "mountain dew"]},
    {"id": 74, "name": "Nước tăng lực, bù khoáng", "keywords": ["nước tăng lực sting", "nước tăng lực redbull", "nước tăng lực monster", "nước tăng lực warrior", "nước pocari sweat", "nước revive"]},
    {"id": 75, "name": "Nước yến", "keywords": ["nước yến sanest", "nước yến ngân nhĩ", "nước yến green bird", "nước yến song yến"]},
    {"id": 76, "name": "Nước ép trái cây", "keywords": ["nước ép twister", "nước ép teppy", "nước ép malee", "nước ép vfresh"]},
    {"id": 77, "name": "Sữa trái cây", "keywords": ["sữa trái cây nutriboost", "sữa trái cây lof kun", "sữa trái cây hero"]},
    {"id": 79, "name": "Rượu", "keywords": ["rượu soju", "rượu vang", "rượu chivas", "rượu nếp"]},
    {"id": 80, "name": "Cà phê lon", "keywords": ["cà phê highlands", "cà phê nescafe lon", "cà phê mr brown"]},
    {"id": 81, "name": "Mật ong", "keywords": ["mật ong nguyên chất", "mật ong rừng", "mật ong hoa rừng"]},
    {"id": 83, "name": "Cà phê hoà tan", "keywords": ["cà phê g7", "cà phê nescafe", "cà phê maccoffee", "cà phê vinacafe", "cà phê trung nguyên"]},
    {"id": 84, "name": "Cà phê pha phin", "keywords": ["cà phê rang xay highlands", "cà phê trung nguyên sáng tạo", "cà phê phin"]},
    {"id": 85, "name": "Trà khô, túi lọc", "keywords": ["trà laphilip", "trà cozy", "trà lipton", "trà dilmah", "trà matcha"]},
    {"id": 86, "name": "Ngũ cốc, yến mạch", "keywords": ["yến mạch quaker", "ngũ cốc kelloog's", "granola sunrise"]},
    {"id": 88, "name": "Ăn vặt các loại", "keywords": ["da heo chiên giòn", "rong biển sấy", "khô gà lá chanh", "khô bò"]},
    {"id": 90, "name": "Bánh quy", "keywords": ["bánh quy goute", "bánh quy cosmo", "bánh quy afc", "bánh quy oreo", "bánh quy ritz", "bánh quy danisa"]},
    {"id": 91, "name": "Bánh tươi, Sandwich", "keywords": ["bánh mì sandwich", "bánh tươi kinh đô", "bánh tươi otto"]},
    {"id": 92, "name": "Bánh bông lan", "keywords": ["bánh custas", "bánh solite", "bánh bông lan kinh đô"]},
    {"id": 93, "name": "Bánh Chocopie", "keywords": ["bánh chocopie", "bánh chocopie dark", "bánh chocopie chuối"]},
    {"id": 94, "name": "Bánh snack", "keywords": ["snack lay's", "snack oishi", "snack poca", "snack swing", "snack doritos", "snack cheetos"]},
    {"id": 95, "name": "Bánh gạo", "keywords": ["bánh gạo one one", "bánh gạo an", "bánh gạo richy", "bánh gạo kobuko"]},
    {"id": 96, "name": "Bánh que", "keywords": ["bánh que pocky", "bánh que toppo", "bánh que pejoy"]},
    {"id": 97, "name": "Bánh quế", "keywords": ["bánh quế cozy", "bánh quế lu", "bánh quế nabati"]},
    {"id": 98, "name": "Kẹo cứng", "keywords": ["kẹo alpenliebe", "kẹo kopiko", "kẹo dynamite", "kẹo xylitol"]},
    {"id": 99, "name": "Kẹo dẻo, kẹo marshmallow", "keywords": ["kẹo dẻo haribo", "kẹo dẻo chupa chups", "kẹo dẻo sugus"]},
    {"id": 100, "name": "Kẹo singum", "keywords": ["singum extra", "singum doublemint", "singum trident"]},
    {"id": 101, "name": "Khô chế biến sẵn", "keywords": ["chà bông heo", "khô mực", "khô bò hai phong", "khô gà"]},
    {"id": 102, "name": "Trái cây sấy", "keywords": ["táo đỏ sấy", "chuối sấy", "mít sấy", "xoài sấy dẻo"]},
    {"id": 103, "name": "Hạt khô", "keywords": ["hạt điều", "hạt hạnh nhân", "hạt óc chó", "hạt dưa", "hạt hướng dương"]},
    {"id": 104, "name": "Rau câu, thạch dừa", "keywords": ["thạch zai zai", "thạch dừa phong nam", "rau câu long hải"]},
    {"id": 105, "name": "Bánh xốp", "keywords": ["bánh xốp nabati", "bánh xốp calcheese", "bánh xốp kitkat"]},
    {"id": 107, "name": "Socola", "keywords": ["socola m&m", "socola snickers", "socola mars", "socola hershey"]},
    {"id": 109, "name": "Băng vệ sinh", "keywords": ["băng vệ sinh diana", "băng vệ sinh kotex", "băng vệ sinh laurier", "băng vệ sinh whisper"]},
    {"id": 110, "name": "Kem đánh răng", "keywords": ["kem đánh răng ps", "kem đánh răng colgate", "kem đánh răng closeup", "kem đánh răng sensodyne"]},
    {"id": 111, "name": "Dầu gội", "keywords": ["dầu gội sunsilk", "dầu gội clear", "dầu gội pantene", "dầu gội rejoice", "dầu gội tresemme", "dầu gội head & shoulders"]},
    {"id": 112, "name": "Dầu xả, kem ủ", "keywords": ["dầu xả dove", "dầu xả sunsilk", "dầu xả pantene", "kem ủ tóc fino"]},
    {"id": 113, "name": "Sữa tắm", "keywords": ["sữa tắm lifebuoy", "sữa tắm dove", "sữa tắm lux", "sữa tắm enchanteur", "sữa tắm hazeline"]},
    {"id": 114, "name": "Nước rửa tay", "keywords": ["nước rửa tay lifebuoy", "nước rửa tay lix", "nước rửa tay dr clean"]},
    {"id": 115, "name": "Lăn xịt khử mùi", "keywords": ["lăn khử mùi nivea", "lăn khử mùi rexona", "xịt khử mùi axe", "sáp khử mùi old spice"]},
    {"id": 116, "name": "Sữa rửa mặt", "keywords": ["sữa rửa mặt hada labo", "sữa rửa mặt senka", "sữa rửa mặt pon's", "sữa rửa mặt cetaphil"]},
    {"id": 117, "name": "Bàn chải, tăm chỉ nha khoa", "keywords": ["bàn chải colgate", "bàn chải ps", "chỉ nha khoa oral-b"]},
    {"id": 118, "name": "Nước súc miệng", "keywords": ["nước súc miệng listerine", "nước súc miệng colgate", "nước súc miệng ps"]},
    {"id": 119, "name": "Xà bông cục", "keywords": ["xà bông lifebuoy", "xà bông lux", "xà bông gervenne", "xà bông safeguard"]},
    {"id": 120, "name": "Giấy vệ sinh", "keywords": ["giấy vệ sinh pulppy", "giấy vệ sinh supremo", "giấy vệ sinh lency", "giấy vệ sinh an an"]},
    {"id": 121, "name": "Khăn giấy", "keywords": ["khăn giấy rút lency", "khăn giấy tempo", "khăn giấy pulppy"]},
    {"id": 122, "name": "Khăn ướt", "keywords": ["khăn ướt mamamy", "khăn ướt kinkin", "khăn ướt fressi"]},
    {"id": 123, "name": "Tẩy trang", "keywords": ["nước tẩy trang simple", "nước tẩy trang l'oreal", "nước tẩy trang senka", "nước tẩy trang bioderma"]},
    {"id": 124, "name": "Kem chống nắng", "keywords": ["kem chống nắng sunplay", "kem chống nắng senka", "kem chống nắng anessa", "kem chống nắng bionet"]},
    {"id": 125, "name": "Sữa dưỡng thể", "keywords": ["sữa dưỡng thể vaseline", "sữa dưỡng thể nivea", "sữa dưỡng thể olay"]},
    {"id": 138, "name": "Nước giặt", "keywords": ["nước giặt omo", "nước giặt ariel", "nước giặt surf", "nước giặt lix", "nước giặt attack"]},
    {"id": 139, "name": "Nước xả", "keywords": ["nước xả comfort", "nước xả downy", "nước xả hygiene"]},
    {"id": 140, "name": "Bột giặt", "keywords": ["bột giặt omo", "bột giặt surf", "bột giặt aba", "bột giặt lix"]},
    {"id": 141, "name": "Nước rửa chén", "keywords": ["nước rửa chén sunlight", "nước rửa chén lix", "nước rửa chén mỹ hảo"]},
    {"id": 142, "name": "Nước lau nhà", "keywords": ["nước lau nhà sunlight", "nước lau nhà gift", "nước lau nhà lix"]},
    {"id": 143, "name": "Tẩy rửa nhà tắm", "keywords": ["nước tẩy vim", "nước tẩy duck", "nước tẩy gift"]},
    {"id": 144, "name": "Bình xịt côn trùng", "keywords": ["bình xịt jumbo", "bình xịt raid", "nhang muỗi jumbo"]},
    {"id": 145, "name": "Xịt phòng, sáp thơm", "keywords": ["sáp thơm ambi pur", "sáp thơm glade", "xịt phòng ambi pur"]},
    {"id": 151, "name": "Tắm gội cho bé", "keywords": ["sữa tắm johnson baby", "sữa tắm lactacyd bb", "sữa tắm purite bb"]},
    {"id": 158, "name": "Pin tiểu", "keywords": ["pin panasonic aa", "pin energizer", "pin duracell"]},
    {"id": 159, "name": "Màng bọc, giấy thấm dầu", "keywords": ["túi đựng thực phẩm", "màng bọc thực phẩm", "giấy thấm dầu"]},
    {"id": 160, "name": "Đồ dùng một lần", "keywords": ["găng tay tự hủy", "muỗng nhựa", "ly giấy", "dĩa giấy"]},
    {"id": 167, "name": "Miếng rửa chén", "keywords": ["miếng rửa chén scotch brite", "cước rửa chén", "mút rửa chén"]}
]

def fetch_bhx_search(keyword):
    """
    Search BHX product API or scrape public BHX search endpoint.
    """
    url = f"https://www.bachhoaxanh.com/aj/category/product?key={urllib.parse.quote(keyword)}&page=1&pageSize=30"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "X-Requested-With": "XMLHttpRequest"
    }
    
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read().decode('utf-8'))
            return data
    except Exception as e:
        return None

def main():
    print("🚀 Starting BHX Product Fetcher...")
    print(f"📦 Total Target Categories: {len(BHX_CATEGORIES)}")
    
    all_products = []
    seen_names = set()
    
    # Test a few keywords first to verify endpoint responsiveness
    test_res = fetch_bhx_search("bia heineken")
    if test_res:
        print("   ✓ BHX Endpoint is responsive!")
    else:
        print("   ⚠️ Direct AJAX endpoint unreachable, fallback mode enabled.")
        
    print("✨ Fetching product data per category keyword...")

if __name__ == '__main__':
    main()
