import React from 'react'
import { Package, Check, XCircle } from 'lucide-react'

const formatPrice = (price) => {
  return new Intl.NumberFormat('vi-VN').format(price)
}

export const ProductCard = ({ product }) => {
  const name = product.name || product.productName || 'Sản phẩm'
  const price = product.unitPrice || product.unit_price || 0
  const qty = product.quantityOnShelf || product.quantity_on_shelf || 0
  const inStock = product.isInStock ?? product.is_in_stock ?? (qty > 0)
  const category = product.categoryName || product.category_name || ''

  return (
    <div className="flex items-center gap-3 p-3 bg-white rounded-xl border border-gray-200 shadow-sm hover:shadow-md transition-shadow ml-9">
      <div className="flex-shrink-0 w-10 h-10 rounded-lg bg-blue-50 flex items-center justify-center">
        <Package size={18} className="text-blue-500" />
      </div>
      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium text-gray-800 truncate">{name}</p>
        <div className="flex items-center gap-2 mt-0.5">
          <span className="text-xs font-semibold text-blue-600">{formatPrice(price)}đ</span>
          {category && (
            <span className="text-[10px] text-gray-400 bg-gray-100 px-1.5 rounded">{category}</span>
          )}
        </div>
      </div>
      <div className="flex-shrink-0 text-right">
        {inStock ? (
          <div className="flex items-center gap-1 text-green-600">
            <Check size={14} />
            <span className="text-xs font-medium">Còn {qty}</span>
          </div>
        ) : (
          <div className="flex items-center gap-1 text-red-500">
            <XCircle size={14} />
            <span className="text-xs font-medium">Hết hàng</span>
          </div>
        )}
      </div>
    </div>
  )
}
