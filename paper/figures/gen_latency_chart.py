import matplotlib.pyplot as plt
import os

# Ensure font family matches IEEE LaTeX (Times New Roman / Computer Modern fallback)
plt.rcParams['font.family'] = 'serif'
plt.rcParams['font.serif'] = ['Times New Roman', 'DejaVu Serif', 'Liberation Serif']

labels = ['PyTorch Native (.pt)', 'ONNX Runtime (.onnx)']
times = [12.5, 0.85]
colors = ['#E06666', '#93C47D']

fig, ax = plt.subplots(figsize=(6, 4.5))
bars = ax.bar(labels, times, color=colors, width=0.45)

for bar in bars:
    yval = bar.get_height()
    ax.text(bar.get_x() + bar.get_width()/2, yval + 0.3, f'{yval} ms', ha='center', va='bottom', fontweight='bold', fontsize=11)

ax.annotate('14.7x Speedup', 
            xy=(0.88, 2.8), 
            xytext=(0.42, 6.5),
            arrowprops=dict(facecolor='#134F5C', edgecolor='#134F5C', shrink=0.08, width=1.5, headwidth=7),
            ha='center', va='center', fontsize=11, fontweight='bold', color='#134F5C')

ax.set_ylabel('Inference Latency (ms)', fontsize=12, fontweight='bold')
ax.set_title('Inference Latency Comparison (Batch Size = 100)', fontsize=13, fontweight='bold', pad=15)
ax.set_ylim(0, 15)
ax.grid(axis='y', linestyle='--', alpha=0.7)
ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)

plt.tight_layout()

# Save both PDF (Vector for IEEE LaTeX) and PNG (300 DPI preview)
output_dir = os.path.dirname(os.path.abspath(__file__))
pdf_path = os.path.join(output_dir, 'latency_comparison.pdf')
png_path = os.path.join(output_dir, 'latency_comparison.png')

plt.savefig(pdf_path, format='pdf', bbox_inches='tight')
plt.savefig(png_path, dpi=300, bbox_inches='tight')
print(f"✅ Successfully generated vector PDF: {pdf_path}")
print(f"✅ Successfully generated PNG preview: {png_path}")
