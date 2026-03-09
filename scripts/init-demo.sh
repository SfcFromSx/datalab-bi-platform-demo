#!/usr/bin/env bash
# init-demo.sh — Seed the DataLab database with demo data for testing
# Usage: bash scripts/init-demo.sh [BASE_URL]
# Requires: curl, jq

set -euo pipefail

BASE="${1:-http://127.0.0.1:8000}"
API="$BASE/api"
WORKSPACE="${DATALAB_WORKSPACE:-demo-hq}"
USER_EMAIL="${DATALAB_USER_EMAIL:-admin@datalab.local}"
AUTH_HEADERS=(
  -H "X-DataLab-Workspace: $WORKSPACE"
  -H "X-DataLab-User-Email: $USER_EMAIL"
)

echo "🚀 DataLab Demo Initializer"
echo "   Target: $API"
echo "   Workspace: $WORKSPACE"
echo "   User: $USER_EMAIL"
echo ""

# Helper: POST JSON and return response body
get() { curl -sf "${AUTH_HEADERS[@]}" "$1"; }
post() {
  curl -sf "${AUTH_HEADERS[@]}" -X POST "$1" \
    -H "Content-Type: application/json" \
    -d "$2"
}
put() {
  curl -sf "${AUTH_HEADERS[@]}" -X PUT "$1" \
    -H "Content-Type: application/json" \
    -d "$2"
}
delete() { curl -sf "${AUTH_HEADERS[@]}" -X DELETE "$1"; }

# ─── Clear existing data ────────────────────────────────────────────
echo "🧹 Clearing existing notebooks..."
for id in $(get "$API/notebooks" | jq -r '.[].id'); do
  delete "$API/notebooks/$id" > /dev/null
  echo "   Deleted notebook $id"
done

echo "🧹 Clearing existing folders..."
for id in $(get "$API/folders" | jq -r '.[].id'); do
  delete "$API/folders/$id" > /dev/null
  echo "   Deleted folder $id"
done

# ─── Create Folders ─────────────────────────────────────────────────
echo ""
echo "📁 Creating folders..."

F_ANALYTICS=$(post "$API/folders" '{"name":"Analytics"}' | jq -r '.id')
echo "   ✅ Analytics ($F_ANALYTICS)"

F_REPORTS=$(post "$API/folders" '{"name":"Reports"}' | jq -r '.id')
echo "   ✅ Reports ($F_REPORTS)"

F_EXPERIMENTS=$(post "$API/folders" '{"name":"Experiments"}' | jq -r '.id')
echo "   ✅ Experiments ($F_EXPERIMENTS)"

# ─── Upload Datasets ───────────────────────────────────────────────
echo ""
echo "📊 Uploading datasets..."

upload() {
  local file="data/$1.csv"
  if [ -f "$file" ]; then
    curl -sf "${AUTH_HEADERS[@]}" -X POST "$API/datasources/upload-csv" \
      -F "file=@$file" > /dev/null
    echo "   ✅ Uploaded $1.csv"
  else
    echo "   ⚠️ Warning: $file not found"
  fi
}

upload "sales"
upload "orders"
upload "user_cohorts"

# ─── Create Notebooks ──────────────────────────────────────────────
echo ""
echo "📓 Creating notebooks..."

# --- 1) Sales Dashboard (in Analytics) ---
NB1=$(post "$API/notebooks" '{"title":"Sales Dashboard","description":"Monthly sales analysis with charts and KPIs"}' | jq -r '.id')
put "$API/notebooks/$NB1" "{\"folder_id\":\"$F_ANALYTICS\"}" > /dev/null
echo "   ✅ Sales Dashboard → Analytics"

post "$API/notebooks/$NB1/cells" '{
  "cell_type":"markdown",
  "source":"# 📊 Sales Dashboard\nMonthly sales data analysis with SQL queries and visualizations.\n\n> Double-click this cell to edit, or add new cells below.",
  "position":0
}' > /dev/null

post "$API/notebooks/$NB1/cells" '{
  "cell_type":"sql",
  "source":"-- Top 10 products by revenue\nSELECT product_name, SUM(quantity * price) AS revenue\nFROM sales\nGROUP BY product_name\nORDER BY revenue DESC\nLIMIT 10;",
  "position":1
}' > /dev/null

post "$API/notebooks/$NB1/cells" '{
  "cell_type":"python",
  "source":"import pandas as pd\n\n# Sample sales data\ndata = {\n    \"month\": [\"Jan\",\"Feb\",\"Mar\",\"Apr\",\"May\",\"Jun\"],\n    \"revenue\": [12500, 15800, 14200, 18900, 21000, 19500],\n    \"orders\": [125, 158, 142, 189, 210, 195]\n}\ndf = pd.DataFrame(data)\nprint(df.to_string(index=False))",
  "position":2
}' > /dev/null

post "$API/notebooks/$NB1/cells" '{
  "cell_type":"chart",
  "source":"{\"title\":{\"text\":\"Monthly Revenue\",\"left\":\"center\"},\"tooltip\":{\"trigger\":\"axis\"},\"xAxis\":{\"type\":\"category\",\"data\":[\"Jan\",\"Feb\",\"Mar\",\"Apr\",\"May\",\"Jun\"]},\"yAxis\":{\"type\":\"value\",\"name\":\"Revenue ($)\"},\"series\":[{\"name\":\"Revenue\",\"type\":\"bar\",\"data\":[12500,15800,14200,18900,21000,19500],\"itemStyle\":{\"color\":\"#5470c6\"}},{\"name\":\"Orders\",\"type\":\"line\",\"yAxisIndex\":0,\"data\":[1250,1580,1420,1890,2100,1950],\"itemStyle\":{\"color\":\"#ee6666\"}}],\"legend\":{\"bottom\":0}}",
  "position":3
}' > /dev/null

# --- 2) User Retention Report (in Reports) ---
NB2=$(post "$API/notebooks" '{"title":"User Retention Report","description":"Weekly and monthly user retention analysis"}' | jq -r '.id')
put "$API/notebooks/$NB2" "{\"folder_id\":\"$F_REPORTS\"}" > /dev/null
echo "   ✅ User Retention Report → Reports"

post "$API/notebooks/$NB2/cells" '{
  "cell_type":"markdown",
  "source":"# 👥 User Retention Analysis\nTracking user retention rates across cohorts.",
  "position":0
}' > /dev/null

post "$API/notebooks/$NB2/cells" '{
  "cell_type":"sql",
  "source":"-- Cohort retention rates\nSELECT\n  cohort_month,\n  COUNT(DISTINCT user_id) AS cohort_size,\n  ROUND(100.0 * COUNT(DISTINCT CASE WHEN months_since_signup = 1 THEN user_id END) / COUNT(DISTINCT user_id), 1) AS m1_retention,\n  ROUND(100.0 * COUNT(DISTINCT CASE WHEN months_since_signup = 3 THEN user_id END) / COUNT(DISTINCT user_id), 1) AS m3_retention\nFROM user_cohorts\nGROUP BY cohort_month\nORDER BY cohort_month;",
  "position":1
}' > /dev/null

post "$API/notebooks/$NB2/cells" '{
  "cell_type":"chart",
  "source":"{\"title\":{\"text\":\"Retention by Cohort\",\"left\":\"center\"},\"tooltip\":{\"trigger\":\"axis\"},\"legend\":{\"bottom\":0},\"xAxis\":{\"type\":\"category\",\"data\":[\"2025-07\",\"2025-08\",\"2025-09\",\"2025-10\",\"2025-11\",\"2025-12\"]},\"yAxis\":{\"type\":\"value\",\"name\":\"%\",\"max\":100},\"series\":[{\"name\":\"M1 Retention\",\"type\":\"line\",\"smooth\":true,\"data\":[85,82,88,84,90,87],\"itemStyle\":{\"color\":\"#91cc75\"}},{\"name\":\"M3 Retention\",\"type\":\"line\",\"smooth\":true,\"data\":[62,58,65,60,68,64],\"itemStyle\":{\"color\":\"#fac858\"}}]}",
  "position":2
}' > /dev/null

# --- 3) A/B Test Results (in Experiments) ---
NB3=$(post "$API/notebooks" '{"title":"A/B Test: Checkout Flow","description":"Comparing new vs old checkout conversion rates"}' | jq -r '.id')
put "$API/notebooks/$NB3" "{\"folder_id\":\"$F_EXPERIMENTS\"}" > /dev/null
echo "   ✅ A/B Test: Checkout Flow → Experiments"

post "$API/notebooks/$NB3/cells" '{
  "cell_type":"markdown",
  "source":"# 🧪 A/B Test: Checkout Flow Redesign\n\n**Hypothesis**: The simplified 2-step checkout will increase conversion by 15%.\n\n| Variant | Users | Conversions | Rate |\n|---------|-------|-------------|------|\n| Control | 5,000 | 350 | 7.0% |\n| Treatment | 5,000 | 425 | 8.5% |\n\n**Result**: +21.4% lift ✅ (p < 0.01)",
  "position":0
}' > /dev/null

post "$API/notebooks/$NB3/cells" '{
  "cell_type":"python",
  "source":"from scipy import stats\n\n# Chi-squared test\ncontrol = [350, 4650]      # [converted, not_converted]\ntreatment = [425, 4575]\n\nchi2, p_value, dof, expected = stats.chi2_contingency([control, treatment])\nprint(f\"Chi-squared: {chi2:.2f}\")\nprint(f\"P-value: {p_value:.4f}\")\nprint(f\"Significant: {p_value < 0.05}\")",
  "position":1
}' > /dev/null

post "$API/notebooks/$NB3/cells" '{
  "cell_type":"chart",
  "source":"{\"title\":{\"text\":\"Conversion Rate: Control vs Treatment\",\"left\":\"center\"},\"tooltip\":{\"trigger\":\"item\",\"formatter\":\"{b}: {c}%\"},\"series\":[{\"type\":\"pie\",\"radius\":[\"40%\",\"70%\"],\"center\":[\"30%\",\"55%\"],\"name\":\"Control\",\"data\":[{\"value\":7,\"name\":\"Converted\",\"itemStyle\":{\"color\":\"#ee6666\"}},{\"value\":93,\"name\":\"Not Converted\",\"itemStyle\":{\"color\":\"#e0e0e0\"}}]},{\"type\":\"pie\",\"radius\":[\"40%\",\"70%\"],\"center\":[\"70%\",\"55%\"],\"name\":\"Treatment\",\"data\":[{\"value\":8.5,\"name\":\"Converted\",\"itemStyle\":{\"color\":\"#91cc75\"}},{\"value\":91.5,\"name\":\"Not Converted\",\"itemStyle\":{\"color\":\"#e0e0e0\"}}]}],\"legend\":{\"bottom\":0}}",
  "position":2
}' > /dev/null

# --- 4) Revenue Forecast (in Analytics) ---
NB4=$(post "$API/notebooks" '{"title":"Revenue Forecast Q2","description":"Predictive model for Q2 2026 revenue"}' | jq -r '.id')
put "$API/notebooks/$NB4" "{\"folder_id\":\"$F_ANALYTICS\"}" > /dev/null
echo "   ✅ Revenue Forecast Q2 → Analytics"

post "$API/notebooks/$NB4/cells" '{
  "cell_type":"markdown",
  "source":"# 💰 Revenue Forecast — Q2 2026\nLinear regression model predicting monthly revenue based on historical trends.",
  "position":0
}' > /dev/null

post "$API/notebooks/$NB4/cells" '{
  "cell_type":"sql",
  "source":"-- Monthly revenue history\nSELECT\n  DATE_TRUNC(''month'', order_date) AS month,\n  SUM(total_amount) AS revenue,\n  COUNT(*) AS total_orders\nFROM orders\nWHERE order_date >= ''2025-01-01''\nGROUP BY 1\nORDER BY 1;",
  "position":1
}' > /dev/null

# --- 5) Data Visualization Gallery (in Analytics — showcases chart cells) ---
NB_VIZ=$(post "$API/notebooks" '{"title":"📊 Chart Gallery","description":"ECharts visualization examples"}' | jq -r '.id')
put "$API/notebooks/$NB_VIZ" "{\"folder_id\":\"$F_ANALYTICS\"}" > /dev/null
echo "   ✅ Chart Gallery → Analytics"

post "$API/notebooks/$NB_VIZ/cells" '{
  "cell_type":"markdown",
  "source":"# 📊 Chart Gallery\nA collection of chart cell examples using ECharts.\n\n> Edit the JSON spec to customize charts. Click the ▶ **Chart Specification** toggle below each chart to see/edit the raw JSON.",
  "position":0
}' > /dev/null

post "$API/notebooks/$NB_VIZ/cells" '{
  "cell_type":"chart",
  "source":"{\"title\":{\"text\":\"Product Category Sales\",\"left\":\"center\"},\"tooltip\":{\"trigger\":\"axis\",\"axisPointer\":{\"type\":\"shadow\"}},\"xAxis\":{\"type\":\"category\",\"data\":[\"Electronics\",\"Clothing\",\"Home\",\"Sports\",\"Books\",\"Food\"]},\"yAxis\":{\"type\":\"value\",\"name\":\"Sales ($K)\"},\"series\":[{\"type\":\"bar\",\"data\":[42,38,25,18,12,30],\"itemStyle\":{\"color\":{\"type\":\"linear\",\"x\":0,\"y\":0,\"x2\":0,\"y2\":1,\"colorStops\":[{\"offset\":0,\"color\":\"#5470c6\"},{\"offset\":1,\"color\":\"#91cc75\"}]}}}]}",
  "position":1
}' > /dev/null

post "$API/notebooks/$NB_VIZ/cells" '{
  "cell_type":"chart",
  "source":"{\"title\":{\"text\":\"Traffic Sources\",\"left\":\"center\"},\"tooltip\":{\"trigger\":\"item\",\"formatter\":\"{b}: {c} ({d}%)\"},\"series\":[{\"type\":\"pie\",\"radius\":\"65%\",\"data\":[{\"value\":335,\"name\":\"Direct\"},{\"value\":310,\"name\":\"Email\"},{\"value\":234,\"name\":\"Social\"},{\"value\":135,\"name\":\"Search\"},{\"value\":148,\"name\":\"Referral\"}],\"emphasis\":{\"itemStyle\":{\"shadowBlur\":10,\"shadowOffsetX\":0,\"shadowColor\":\"rgba(0,0,0,0.5)\"}}}],\"legend\":{\"bottom\":0,\"left\":\"center\"}}",
  "position":2
}' > /dev/null

post "$API/notebooks/$NB_VIZ/cells" '{
  "cell_type":"chart",
  "source":"{\"title\":{\"text\":\"Weekly Active Users\",\"left\":\"center\"},\"tooltip\":{\"trigger\":\"axis\"},\"xAxis\":{\"type\":\"category\",\"data\":[\"W1\",\"W2\",\"W3\",\"W4\",\"W5\",\"W6\",\"W7\",\"W8\"]},\"yAxis\":{\"type\":\"value\"},\"series\":[{\"name\":\"DAU\",\"type\":\"line\",\"smooth\":true,\"areaStyle\":{\"color\":{\"type\":\"linear\",\"x\":0,\"y\":0,\"x2\":0,\"y2\":1,\"colorStops\":[{\"offset\":0,\"color\":\"rgba(84,112,198,0.5)\"},{\"offset\":1,\"color\":\"rgba(84,112,198,0.05)\"}]}},\"data\":[820,932,901,1034,1290,1330,1420,1500],\"itemStyle\":{\"color\":\"#5470c6\"}}]}",
  "position":3
}' > /dev/null

# --- 6) Quick Notes (uncategorized) ---
NB5=$(post "$API/notebooks" '{"title":"Quick Notes","description":"Scratch pad for ad-hoc queries"}' | jq -r '.id')
echo "   ✅ Quick Notes (uncategorized)"

post "$API/notebooks/$NB5/cells" '{
  "cell_type":"markdown",
  "source":"# 📝 Quick Notes\nUse this notebook as a scratch pad for ad-hoc queries and ideas.\n\n- Try dragging this notebook into a folder\n- Double-click to rename\n- Hover to see the delete button",
  "position":0
}' > /dev/null

post "$API/notebooks/$NB5/cells" '{
  "cell_type":"sql",
  "source":"-- Quick check: table row counts\nSELECT ''users'' AS table_name, COUNT(*) AS rows FROM users\nUNION ALL\nSELECT ''orders'', COUNT(*) FROM orders\nUNION ALL\nSELECT ''products'', COUNT(*) FROM products;",
  "position":1
}' > /dev/null

# --- 6) Meeting Notes (uncategorized) ---
NB6=$(post "$API/notebooks" '{"title":"Team Standup Notes","description":"Weekly team meeting action items"}' | jq -r '.id')
echo "   ✅ Team Standup Notes (uncategorized)"

post "$API/notebooks/$NB6/cells" '{
  "cell_type":"markdown",
  "source":"# 🗓️ Team Standup — March 4\n\n## Action Items\n- [ ] Review A/B test results\n- [ ] Update revenue dashboard with Q1 actuals\n- [ ] Schedule data pipeline review\n\n## Decisions\n- Move to weekly retention reports\n- Sunset legacy dashboard by end of month",
  "position":0
}' > /dev/null

# --- 7) Enterprise Runtime Demo (in Analytics) ---
NB_RUNTIME=$(post "$API/notebooks" '{"title":"Enterprise Runtime Demo","description":"Validates stateless DAG cell agents, file-backed IPC, and AI editing progress"}' | jq -r '.id')
put "$API/notebooks/$NB_RUNTIME" "{\"folder_id\":\"$F_ANALYTICS\"}" > /dev/null
echo "   ✅ Enterprise Runtime Demo → Analytics"

post "$API/notebooks/$NB_RUNTIME/cells" '{
  "cell_type":"markdown",
  "source":"# Enterprise Runtime Demo\nEach cell now runs as its own cell agent.\n\n- A stateless DAG is rebuilt on every execution\n- Cell agents exchange context through file-backed inbox/outbox messages\n- Every cell has its own workspace and runtime manifest\n\nRecommended checks:\n1. Run the chart cell directly and confirm upstream SQL + Python + SQL cells execute automatically.\n2. Expand the `Cell Agent Runtime` panel under any executed cell.\n3. Use AI Edit on any cell and watch the right-side progress rail show DAG and IPC stages.",
  "position":0
}' > /dev/null

post "$API/notebooks/$NB_RUNTIME/cells" '{
  "cell_type":"sql",
  "source":"-- output: sales_summary\nSELECT\n  product_name,\n  SUM(quantity * price) AS revenue,\n  SUM(quantity) AS units_sold\nFROM sales\nGROUP BY product_name\nORDER BY revenue DESC\nLIMIT 5;",
  "position":1
}' > /dev/null

post "$API/notebooks/$NB_RUNTIME/cells" '{
  "cell_type":"python",
  "source":"product_metrics = sales_summary.assign(\n    avg_selling_price=sales_summary[\"revenue\"] / sales_summary[\"units_sold\"]\n).sort_values(\"revenue\", ascending=False)\n\nprint(product_metrics.to_string(index=False))",
  "position":2
}' > /dev/null

post "$API/notebooks/$NB_RUNTIME/cells" '{
  "cell_type":"sql",
  "source":"-- output: premium_products\nSELECT\n  product_name,\n  revenue,\n  avg_selling_price\nFROM product_metrics\nWHERE revenue >= 5000\nORDER BY revenue DESC;",
  "position":3
}' > /dev/null

post "$API/notebooks/$NB_RUNTIME/cells" '{
  "cell_type":"chart",
  "source":"{\"data_source\":\"premium_products\",\"chart_type\":\"bar\",\"title\":{\"text\":\"Premium Products\",\"left\":\"center\"},\"x_field\":\"product_name\",\"y_field\":[\"revenue\",\"avg_selling_price\"],\"legend\":{\"bottom\":0}}",
  "position":4
}' > /dev/null

post "$API/notebooks/$NB_RUNTIME/cells" '{
  "cell_type":"markdown",
  "source":"## Live Notebook Summary\nRows in filtered SQL output: {{ premium_products.row_count }}\n\nColumns in filtered SQL output: {{ premium_products.columns }}\n\nPreview rows: {{ premium_products.preview }}",
  "position":5
}' > /dev/null

# ─── Summary ────────────────────────────────────────────────────────
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ Demo data created successfully!"
echo ""
echo "   📁 3 folders: Analytics, Reports, Experiments"
echo "   📓 8 notebooks (6 in folders, 2 uncategorized)"
echo "   📝 ~25 cells (markdown, sql, python, chart)"
echo "   🧪 Enterprise Runtime Demo validates SQL → Python → SQL → Chart → Markdown cell agents"
echo ""
echo "   Open http://localhost:5171 to explore!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
