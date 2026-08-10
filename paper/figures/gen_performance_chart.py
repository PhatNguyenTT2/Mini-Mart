import matplotlib.pyplot as plt
import numpy as np
import os

# 1. Cấu hình phông chữ Serif chuẩn IEEE
plt.rcParams['font.family'] = 'serif'
plt.rcParams['font.serif'] = ['Times New Roman', 'DejaVu Serif', 'Liberation Serif']

# 2. Dữ liệu đầu vào
variants = ['Random', 'Apriori', 'SBERT', 'Item-CF', 'Noisy 10%', 'Deep-Only', 'Hybrid']
hit_rates = [0.1620, 0.0700, 0.3260, 0.4720, 0.4200, 0.4840, 0.4940]
gauc = [0.5324, 0.7575, 0.6869, 0.8488, 0.8463, 0.8501, 0.8507]

x = np.arange(len(variants))
fig, ax1 = plt.subplots(figsize=(10, 5.5))

# 3. Cố định giới hạn trục Y
ax1_min, ax1_max = 0, 0.65
ax2_min, ax2_max = 0.40, 1.05

# Vẽ biểu đồ cột (Hit Rate)
color1 = '#3B82F6'
bars = ax1.bar(x, hit_rates, color=color1, width=0.48, label='Hit Rate@10', alpha=0.85, zorder=2)
ax1.set_ylabel('Hit Rate@10', color='#1D4ED8', fontsize=12, fontweight='bold')
ax1.tick_params(axis='y', labelcolor='#1D4ED8')
ax1.set_xticks(x)
ax1.set_xticklabels(variants, rotation=15, ha='right', fontsize=10, fontweight='bold')
ax1.set_ylim(ax1_min, ax1_max)

# Vẽ biểu đồ đường (GAUC)
ax2 = ax1.twinx()
color2 = '#DC2626'
line = ax2.plot(x, gauc, color=color2, marker='o', linewidth=2.5, markersize=8, label='GAUC', zorder=5)
ax2.set_ylabel('Group AUC (GAUC)', color=color2, fontsize=12, fontweight='bold')
ax2.tick_params(axis='y', labelcolor=color2)
ax2.set_ylim(ax2_min, ax2_max)

# 4. CÂN CHỈNH VỊ TRÍ NHÃN TRÁNH CHE KHUẤT
for i, bar in enumerate(bars):
    y_bar = hit_rates[i]
    y_node = gauc[i]
    
    # Quy đổi cao độ node đỏ sang thang ax1
    norm_node = (y_node - ax2_min) / (ax2_max - ax2_min)
    y_node_on_ax1 = norm_node * (ax1_max - ax1_min) + ax1_min
    
    # Lấy điểm cao nhất làm neo cho số xanh
    anchor_y = max(y_bar, y_node_on_ax1)
    
    # --- Số Xanh (Hit Rate) ---
    # Đẩy lên trên +8pt tính từ đỉnh cao nhất
    ax1.annotate(f'{y_bar:.4f}', 
                 (bar.get_x() + bar.get_width()/2, anchor_y),
                 textcoords="offset points", 
                 xytext=(0, 8), 
                 ha='center', va='bottom', 
                 fontsize=8.5, fontweight='bold', color='#1D4ED8', zorder=7)

    # --- Số Đỏ (GAUC) ---
    # Tăng offset_y xuống -18pt để vượt qua hoàn toàn độ dày của đường line và marker đỏ
    ax2.annotate(f'{y_node:.4f}', 
                 (x[i], y_node), 
                 textcoords="offset points", 
                 xytext=(0, -18),  # Đã điều chỉnh hạ sâu hơn để không dính line
                 ha='center', va='top', 
                 fontsize=8.5, fontweight='bold', color='#991B1B', zorder=6)

# 5. Hoàn thiện đồ họa
ax1.set_title('Full-Catalog Ablation Study & Baseline Comparison (1,380 SKUs)', fontsize=13.5, fontweight='bold', pad=15)

lines1, labels1 = ax1.get_legend_handles_labels()
lines2, labels2 = ax2.get_legend_handles_labels()
ax1.legend(lines1 + lines2, labels1 + labels2, loc="upper left", bbox_to_anchor=(0.02, 0.96), frameon=True, facecolor='white', framealpha=0.95)

ax1.grid(axis='y', linestyle='--', alpha=0.3, zorder=1)
plt.tight_layout()

# Lưu kết quả
output_dir = os.path.dirname(os.path.abspath(__file__))
pdf_path = os.path.join(output_dir, 'performance_ablation_adjusted.pdf')
png_path = os.path.join(output_dir, 'performance_ablation_adjusted.png')

plt.savefig(pdf_path, format='pdf', bbox_inches='tight')
plt.savefig(png_path, dpi=300, bbox_inches='tight')