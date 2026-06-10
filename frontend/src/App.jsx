import { BrowserRouter as Router, Routes, Route, Navigate } from "react-router-dom";
import { Dashboard, ViewProduct, Products, ProductBatches, LoginSignup, Orders, Categories, Employees, Customers, Suppliers, Inventories, DetailInventories, PurchaseReports, SalesReports, ProfitReports, Roles, POSManagement, Settings, NoAccess } from "./pages";
import InventoryReport from "./pages/reports/InventoryReport";
import EmployeeSalesReport from "./pages/reports/EmployeeSales";
import CustomerSalesReport from "./pages/reports/CustomerSales";
import { ProductQRCodes } from "./pages/ProductQRCodes";
import { StockOuts } from "./pages/StockOuts";
import Locations from "./pages/Locations";
import { POSLogin, POSMain } from "./pages/pos";
import PurchaseOrders from "./pages/PurchaseOrders";
import Payments from "./pages/Payments";
import ProtectedRoute from "./components/ProtectedRoute";
import { ProtectedLayout } from "./components/ProtectedLayout";
import { PERMISSIONS } from "./utils/permissions";
import { ChatProvider } from "./contexts/ChatContext";
import "./App.css";

function App() {
  return (
    <Router>
      <Routes>
        {/* Auth Routes - Public */}
        <Route path="/" element={<LoginSignup />} />
        <Route path="/signup" element={<LoginSignup />} />
        <Route path="/no-access" element={<NoAccess />} />

        {/* POS Routes - Separate authentication flow */}
        <Route path="/pos-login" element={<POSLogin />} />
        <Route
          path="/pos"
          element={
            <ChatProvider>
              <POSMain />
            </ChatProvider>
          }
        />

        {/* Protected Routes - All wrapped in shared ProtectedLayout */}
        <Route element={<ProtectedLayout />}>
          {/* Dashboard */}
          <Route
            path="/dashboard"
            element={
              <ProtectedRoute requiredPermission={PERMISSIONS.VIEW_DASHBOARD}>
                <Dashboard />
              </ProtectedRoute>
            }
          />

          {/* Products Routes */}
          <Route
            path="/products/view"
            element={
              <ProtectedRoute requiredPermission={PERMISSIONS.MANAGE_PRODUCTS}>
                <ViewProduct />
              </ProtectedRoute>
            }
          />
          <Route
            path="/products"
            element={
              <ProtectedRoute requiredPermission={PERMISSIONS.MANAGE_PRODUCTS}>
                <Products />
              </ProtectedRoute>
            }
          />
          <Route
            path="/products/:productId/batches"
            element={
              <ProtectedRoute requiredPermission={PERMISSIONS.MANAGE_PRODUCTS}>
                <ProductBatches />
              </ProtectedRoute>
            }
          />
          <Route
            path="/product-qr-codes"
            element={
              <ProtectedRoute requiredPermission={PERMISSIONS.MANAGE_PRODUCTS}>
                <ProductQRCodes />
              </ProtectedRoute>
            }
          />

          {/* Orders */}
          <Route
            path="/orders"
            element={
              <ProtectedRoute requiredPermission={PERMISSIONS.MANAGE_ORDERS}>
                <Orders />
              </ProtectedRoute>
            }
          />

          {/* Categories */}
          <Route
            path="/categories"
            element={
              <ProtectedRoute requiredPermission={PERMISSIONS.MANAGE_CATEGORIES}>
                <Categories />
              </ProtectedRoute>
            }
          />

          {/* Employees & Roles */}
          <Route
            path="/employees"
            element={
              <ProtectedRoute requiredPermission={PERMISSIONS.MANAGE_EMPLOYEES}>
                <Employees />
              </ProtectedRoute>
            }
          />
          <Route
            path="/roles"
            element={
              <ProtectedRoute requiredPermission={PERMISSIONS.MANAGE_ROLES}>
                <Roles />
              </ProtectedRoute>
            }
          />

          {/* Customers */}
          <Route
            path="/customers"
            element={
              <ProtectedRoute requiredPermission={PERMISSIONS.MANAGE_CUSTOMERS}>
                <Customers />
              </ProtectedRoute>
            }
          />

          {/* Suppliers */}
          <Route
            path="/suppliers"
            element={
              <ProtectedRoute requiredPermission={PERMISSIONS.MANAGE_SUPPLIERS}>
                <Suppliers />
              </ProtectedRoute>
            }
          />

          {/* Inventory Routes */}
          <Route
            path="/inventories"
            element={<Navigate to="/inventory/management" replace />}
          />
          <Route
            path="/inventory/management"
            element={
              <ProtectedRoute requiredPermission={PERMISSIONS.MANAGE_INVENTORY}>
                <Inventories />
              </ProtectedRoute>
            }
          />
          <Route
            path="/inventory/detail/:productId"
            element={
              <ProtectedRoute requiredPermission={PERMISSIONS.MANAGE_INVENTORY}>
                <DetailInventories />
              </ProtectedRoute>
            }
          />
          <Route
            path="/inventory/purchase-orders"
            element={
              <ProtectedRoute requiredPermission={PERMISSIONS.MANAGE_INVENTORY}>
                <PurchaseOrders />
              </ProtectedRoute>
            }
          />
          <Route
            path="/inventory/stock-outs"
            element={
              <ProtectedRoute requiredPermission={PERMISSIONS.MANAGE_INVENTORY}>
                <StockOuts />
              </ProtectedRoute>
            }
          />
          <Route
            path="/inventory/locations"
            element={
              <ProtectedRoute requiredPermission={PERMISSIONS.MANAGE_INVENTORY}>
                <Locations />
              </ProtectedRoute>
            }
          />

          {/* Store Locations - Redirect to unified Locations page */}
          <Route
            path="/products/store-locations"
            element={<Navigate to="/inventory/locations" replace />}
          />

          {/* Payments */}
          <Route
            path="/payments"
            element={
              <ProtectedRoute requiredPermission={PERMISSIONS.MANAGE_PAYMENTS}>
                <Payments />
              </ProtectedRoute>
            }
          />

          {/* Reports Routes */}
          <Route
            path="/reports/purchase"
            element={
              <ProtectedRoute requiredPermission={PERMISSIONS.VIEW_REPORTS}>
                <PurchaseReports />
              </ProtectedRoute>
            }
          />
          <Route
            path="/reports/sales"
            element={
              <ProtectedRoute requiredPermission={PERMISSIONS.VIEW_REPORTS}>
                <SalesReports />
              </ProtectedRoute>
            }
          />
          <Route
            path="/reports/profit"
            element={
              <ProtectedRoute requiredPermission={PERMISSIONS.VIEW_REPORTS}>
                <ProfitReports />
              </ProtectedRoute>
            }
          />
          <Route
            path="/reports/inventory"
            element={
              <ProtectedRoute requiredPermission={PERMISSIONS.VIEW_REPORTS}>
                <InventoryReport />
              </ProtectedRoute>
            }
          />
          <Route
            path="/reports/employee-sales"
            element={
              <ProtectedRoute requiredPermission={PERMISSIONS.VIEW_REPORTS}>
                <EmployeeSalesReport />
              </ProtectedRoute>
            }
          />
          <Route
            path="/reports/customer-sales"
            element={
              <ProtectedRoute requiredPermission={PERMISSIONS.VIEW_REPORTS}>
                <CustomerSalesReport />
              </ProtectedRoute>
            }
          />

          {/* POS Management */}
          <Route
            path="/pos-management"
            element={
              <ProtectedRoute requiredPermission={PERMISSIONS.MANAGE_POS}>
                <POSManagement />
              </ProtectedRoute>
            }
          />

          {/* Settings */}
          <Route
            path="/settings"
            element={
              <ProtectedRoute requiredPermission={[PERMISSIONS.MANAGER_SETTING, PERMISSIONS.ADMIN_SETTING]}>
                <Settings />
              </ProtectedRoute>
            }
          />
        </Route>
      </Routes>
    </Router>
  );
}

export default App;
