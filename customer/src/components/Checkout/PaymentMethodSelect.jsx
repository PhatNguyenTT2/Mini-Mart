export function PaymentMethodSelect({ paymentMethod, setPaymentMethod }) {
  return (
    <div className="bg-white border border-gray-200 rounded-xl p-6 mt-6">
      <h2 className="font-bold text-gray-800 text-xl mb-4">Payment Method</h2>
      
      <div className="space-y-4">
        {/* VNPay Option */}
        <label 
          className={`flex items-start p-4 border rounded-lg cursor-pointer transition-colors ${
            paymentMethod === 'vnpay' ? 'border-emerald-500 bg-emerald-50' : 'border-gray-200 hover:border-emerald-300'
          }`}
        >
          <div className="flex items-center h-5">
              <input 
                type="radio" 
                name="paymentMethod" 
                value="vnpay" 
                checked={paymentMethod === 'vnpay'} 
                onChange={(e) => setPaymentMethod(e.target.value)}
                className="w-4 h-4 text-emerald-600 focus:ring-emerald-500" 
              />
          </div>
          <div className="ml-3 text-sm">
              <span className="font-semibold text-gray-800">VNPay (ATM Card, Visa/Mastercard, VNPAY-QR)</span>
              <p className="text-gray-500 mt-1">Safe and secure payment via VNPay gateway.</p>
          </div>
        </label>

        {/* COD Option */}
        <label 
          className={`flex items-start p-4 border rounded-lg cursor-pointer transition-colors ${
            paymentMethod === 'cod' ? 'border-emerald-500 bg-emerald-50' : 'border-gray-200 hover:border-emerald-300'
          }`}
        >
          <div className="flex items-center h-5">
              <input 
                type="radio" 
                name="paymentMethod" 
                value="cod" 
                checked={paymentMethod === 'cod'} 
                onChange={(e) => setPaymentMethod(e.target.value)}
                className="w-4 h-4 text-emerald-600 focus:ring-emerald-500" 
              />
          </div>
          <div className="ml-3 text-sm">
              <span className="font-semibold text-gray-800">Cash on Delivery (COD)</span>
              <p className="text-gray-500 mt-1">Pay when you receive the order.</p>
          </div>
        </label>
      </div>
    </div>
  );
}
