/**
 * Intent Resolver — Keyword/regex-based intent classification
 * Lightweight, no AI needed. Classifies user messages into actionable intents.
 */

const INTENT_PATTERNS = {
    // ── WRITE/ACTION INTENTS (High priority to avoid general text matching) ──
    CANCEL_ORDER: {
        keywords: ['hủy đơn', 'cancel', 'bỏ đơn'],
        writeAction: true,
        description: 'Hủy đơn hàng'
    },
    TRACK_ORDER: {
        keywords: ['/đơn.*ở đâu/', 'theo dõi đơn', 'lịch trình đơn'],
        writeAction: true,
        description: 'Theo dõi chi tiết quá trình vận chuyển đơn hàng'
    },
    PAYMENT_CHECK: {
        keywords: ['kiểm tra thanh toán', 'kiểm tra hoá đơn', 'check bill'],
        writeAction: false,
        employeeOnly: true,
        description: 'Kiểm tra thanh toán đơn hàng (Nhân viên)'
    },
    CHECKOUT_GUIDE: {
        keywords: ['thanh toán', 'checkout', 'hướng dẫn thanh toán', 'mua hàng'],
        writeAction: true,
        customerOnly: true,
        description: 'Hướng dẫn thanh toán giỏ hàng'
    },
    VIEW_CART: {
        keywords: ['xem giỏ hàng', 'giỏ hàng của tôi', 'trong giỏ có gì'],
        writeAction: true,
        description: 'Hiển thị giỏ hàng hiện tại'
    },
    REMOVE_FROM_CART: {
        keywords: ['/bỏ.*ra/', '/xóa.*giỏ/', '/bỏ.*khỏi.*giỏ/'],
        writeAction: true,
        description: 'Xóa sản phẩm khỏi giỏ hàng'
    },
    UPDATE_CART_ITEM: {
        keywords: ['/tăng.*(lên|thành)/', '/giảm.*(xuống|thành)/', '/đổi.*số lượng/', 'cập nhật số lượng', 'sửa số lượng'],
        writeAction: true,
        description: 'Cập nhật số lượng sản phẩm trong giỏ hàng'
    },
    ADD_TO_CART: {
        keywords: ['/thêm.*(vào)?.*giỏ/', '/bỏ.*(vào)?.*giỏ/', '/^thêm\\b/', '/\\bthêm\\s+\\d+/', '/^mua\\b/', '/^lấy\\b/', '/\\bmua\\s+\\d+/', '/\\blấy\\s+\\d+/'],
        writeAction: true,
        description: 'Thêm sản phẩm vào giỏ hàng khách hàng'
    },
    CREATE_ORDER: {
        keywords: ['tạo đơn', 'lập hóa đơn', 'đặt hàng'],
        writeAction: true,
        description: 'Tạo đơn hàng mới (Nhân viên)'
    },
    UPDATE_ORDER: {
        keywords: ['sửa đơn', 'thêm sp vào đơn', 'cập nhật đơn'],
        writeAction: true,
        employeeOnly: true,
        description: 'Cập nhật chi tiết đơn hàng (Nhân viên)'
    },
    POS_ADD_ITEM: {
        keywords: ['thêm', 'bán'],
        writeAction: true,
        employeeOnly: true,
        description: 'Thêm sản phẩm vào giỏ hàng POS (Nhân viên)'
    },
    POS_HOLD_ORDER: {
        keywords: ['lưu hóa đơn', 'hold', 'giữ đơn', 'lưu đơn', 'tạm lưu'],
        writeAction: true,
        employeeOnly: true,
        description: 'Lưu giỏ hàng POS thành hóa đơn tạm (Hold Order)'
    },
    POS_CHECKOUT: {
        keywords: ['thanh toán', 'payment', 'xuất hóa đơn', 'checkout', 'tính tiền'],
        writeAction: true,
        employeeOnly: true,
        description: 'Mở giao diện thanh toán POS'
    },
    VIEW_ORDER_HISTORY: {
        keywords: ['lịch sử đơn', 'history', 'đơn đã tạo', 'lịch sử đơn hàng'],
        writeAction: false,
        employeeOnly: true,
        description: 'Mở lịch sử đơn hàng POS (Nhân viên)'
    },
    MANAGE_BATCH_DISCOUNT: {
        keywords: ['giảm giá', 'chiết khấu', 'sale', 'hạ giá', 'set giảm giá', 'discount', 'áp dụng giảm giá'],
        writeAction: true,
        managerOnly: true,
        description: 'Cấu hình giảm giá lô hàng sản phẩm (Manager)'
    },
    REPORT_SALES: {
        keywords: ['doanh thu', 'revenue', 'doanh số'],
        writeAction: false,
        managerOnly: true,
        description: 'Báo cáo doanh thu (Manager)'
    },
    REPORT_TOP_PRODUCTS: {
        keywords: ['bán chạy nhất', 'top sản phẩm', 'bán chạy', 'sp chạy'],
        writeAction: false,
        managerOnly: true,
        description: 'Báo cáo top bán chạy (Manager)'
    },
    REPORT_LOW_STOCK: {
        keywords: ['hàng sắp hết', 'low stock', 'sắp hết hàng', 'cực tiểu'],
        writeAction: false,
        managerOnly: true,
        description: 'Báo cáo hàng tồn kho sắp hết (Manager)'
    },
    REPORT_PROFIT: {
        keywords: ['lợi nhuận', 'profit', 'lãi ròng'],
        writeAction: false,
        managerOnly: true,
        description: 'Báo cáo lợi nhuận (Manager)'
    },
    MANAGE_CUSTOMER_SEARCH: {
        keywords: ['tìm khách hàng', 'tìm khách', 'search khách'],
        writeAction: false,
        managerOnly: true,
        description: 'Tìm kiếm hồ sơ khách hàng (Manager)'
    },
    MANAGE_CUSTOMER_UPDATE: {
        keywords: ['nâng hạng', 'cập nhật hạng', 'đổi hạng'],
        writeAction: true,
        managerOnly: true,
        description: 'Cập nhật phân loại khách hàng (Manager)'
    },
    MANAGE_CUSTOMER_LIST: {
        keywords: ['danh sách khách', 'ds khách VIP', 'ds khách hàng'],
        writeAction: false,
        managerOnly: true,
        description: 'Danh sách khách hàng (Manager)'
    },
    MANAGE_SUPPLIER_LIST: {
        keywords: ['danh sách nhà cung cấp', 'ds ncc', 'danh sách ncc'],
        writeAction: false,
        managerOnly: true,
        description: 'Danh sách nhà cung cấp (Manager)'
    },
    MANAGE_SUPPLIER_SEARCH: {
        keywords: ['thông tin ncc', 'tìm ncc', 'ncc vinamilk'],
        writeAction: false,
        managerOnly: true,
        description: 'Thông tin nhà cung cấp (Manager)'
    },
    MANAGE_INVENTORY_CHECK: {
        keywords: ['kiểm tra tồn kho kho chính', 'kiểm kho', 'tổng tồn'],
        writeAction: false,
        managerOnly: true,
        description: 'Kiểm tra tồn kho tổng quát (Manager)'
    },
    MANAGE_INVENTORY_STOCKOUT: {
        keywords: ['hết hàng', 'cháy hàng', 'sản phẩm nào hết'],
        writeAction: false,
        managerOnly: true,
        description: 'Danh sách sản phẩm hết hàng (Manager)'
    },
    MANAGE_INVENTORY_VIEW: {
        keywords: ['mở quản lý kho', 'quản lý kho'],
        writeAction: false,
        managerOnly: true,
        description: 'Mở trang quản lý kho (Manager)'
    },


    // ── READ INTENTS (Lower priority) ───────────
    CHECK_STOCK: {
        keywords: ['tồn kho', 'còn hàng', 'còn không', 'hết hàng', 'có còn', 'còn bao nhiêu', 'trên kệ', '/còn.*kệ/', 'stock', 'inventory', 'số lượng còn'],
        description: 'Kiểm tra tồn kho sản phẩm'
    },
    CHECK_PRICE: {
        keywords: ['giá', 'bao nhiêu', 'price', 'giá bán', 'giá tiền', 'chi phí'],
        description: 'Kiểm tra giá sản phẩm'
    },
    ORDER_STATUS: {
        keywords: ['đơn hàng', 'order', 'tracking', 'giao hàng', 'trạng thái đơn', 'đơn #', 'mã đơn'],
        description: 'Kiểm tra trạng thái đơn hàng'
    },
    RECOMMENDATION: {
        keywords: ['gợi ý', 'recommend', 'đề xuất', 'tư vấn', 'nên mua', 'mua gì',
            'có gì ngon', 'giới thiệu', 'best seller', 'bán chạy', 'phổ biến',
            'muốn mua', 'cần mua', 'mua cho', 'mua sắm', 'mua gì đó', 'mua đồ',
            'cho tôi', 'cho xem', 'cho mình',
            'ăn kèm', 'kèm theo', 'đi kèm',
            'muốn nấu', 'nấu gì', 'làm món', 'nấu ăn', 'nấu lẩu'],
        description: 'Gợi ý sản phẩm (RAG Pipeline)'
    },
    SEARCH_PRODUCT: {
        keywords: ['tìm', 'search', 'có gì', 'sản phẩm nào', 'loại nào', 'tìm kiếm'],
        description: 'Tìm kiếm sản phẩm'
    },
    HELP: {
        keywords: ['help', 'giúp', 'hướng dẫn', 'làm sao', 'cách', 'hỗ trợ'],
        description: 'Yêu cầu hỗ trợ'
    }
};

/**
 * Resolves intent of a user message.
 * Specific pattern order ensures longer/more specific phrases match before shorter keywords.
 * @param {string} message 
 * @param {string} userType - 'customer' or 'employee'
 */
function resolveIntent(message, userType = 'customer') {
    const normalizedMsg = message.toLowerCase().trim();

    // 1. Priority pre-check for RECOMMENDATION to prevent false matches with ADD_TO_CART regexes or SEARCH_PRODUCT.
    // If it's a structural cart write action (contains 'giỏ', 'xóa', 'hủy', 'tạo đơn'), do not intercept.
    const isCartOrOrderWrite = normalizedMsg.includes('giỏ') || normalizedMsg.includes('xóa') || normalizedMsg.includes('hủy') || normalizedMsg.includes('tạo đơn');
    if (!isCartOrOrderWrite) {
        const recConfig = INTENT_PATTERNS.RECOMMENDATION;
        for (const keyword of recConfig.keywords) {
            if (normalizedMsg.includes(keyword)) {
                const TRANSACTIONAL_VERBS = ['muốn mua', 'cần mua', 'mua cho', 'đặt', 'lấy', 'cần', 'mua'];
                const isTransactional = TRANSACTIONAL_VERBS.some(v => normalizedMsg.includes(v));
                return {
                    intent: 'RECOMMENDATION',
                    confidence: 'priority_keyword_match',
                    matchedKeyword: keyword,
                    description: recConfig.description,
                    writeAction: false,
                    isTransactional
                };
            }
        }
    }

    for (const [intent, config] of Object.entries(INTENT_PATTERNS)) {
        // Enforce manager-only validation at intent resolution stage
        if (config.managerOnly && userType !== 'manager') {
            continue;
        }
        // Enforce employee-only action validation at intent resolution stage (Managers also have access)
        if (config.employeeOnly && userType !== 'employee' && userType !== 'manager') {
            continue;
        }
        // Skip customer-only intents for employees/managers (e.g. CHECKOUT_GUIDE → POS_CHECKOUT)
        if (config.customerOnly && (userType === 'employee' || userType === 'manager')) {
            continue;
        }

        for (const keyword of config.keywords) {
            if (keyword.startsWith('/') && keyword.endsWith('/')) {
                const regex = new RegExp(keyword.slice(1, -1), 'i');
                if (regex.test(normalizedMsg)) {
                    const finalIntent = ((userType === 'employee' || userType === 'manager') && intent === 'ADD_TO_CART') ? 'POS_ADD_ITEM' : intent;
                    return {
                        intent: finalIntent,
                        confidence: 'regex_match',
                        matchedKeyword: keyword,
                        description: finalIntent === 'POS_ADD_ITEM' ? INTENT_PATTERNS.POS_ADD_ITEM.description : config.description,
                        writeAction: config.writeAction || false
                    };
                }
            } else if (normalizedMsg.includes(keyword)) {
                const finalIntent = ((userType === 'employee' || userType === 'manager') && intent === 'ADD_TO_CART') ? 'POS_ADD_ITEM' : intent;
                return {
                    intent: finalIntent,
                    confidence: 'keyword_match',
                    matchedKeyword: keyword,
                    description: finalIntent === 'POS_ADD_ITEM' ? INTENT_PATTERNS.POS_ADD_ITEM.description : config.description,
                    writeAction: config.writeAction || false
                };
            }
        }
    }

    return {
        intent: 'FREE_CHAT',
        confidence: 'default',
        matchedKeyword: null,
        description: 'Trò chuyện tự do với AI',
        writeAction: false
    };
}

function getAllIntents() {
    return Object.entries(INTENT_PATTERNS).map(([key, val]) => ({
        intent: key,
        keywords: val.keywords,
        description: val.description,
        writeAction: val.writeAction || false,
        employeeOnly: val.employeeOnly || false
    }));
}

module.exports = { resolveIntent, getAllIntents, INTENT_PATTERNS };
