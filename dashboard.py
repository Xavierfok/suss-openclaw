"""
Heyva Health Lead Tracking Dashboard
Run with: streamlit run dashboard.py
"""
import streamlit as st
import pandas as pd
import json
import os
from datetime import datetime

# Config
DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "leads_data")
TRACKING_FILE = os.path.join(DATA_DIR, "tracking.json")
ANALYZED_FILE = os.path.join(DATA_DIR, "indonesia_analyzed.json")

# Page config
st.set_page_config(page_title="Heyva Health Leads", page_icon="🏥", layout="wide")

# --- Data Loading ---

@st.cache_data(ttl=3600)  # refresh every hour
def load_leads():
    if not os.path.exists(ANALYZED_FILE):
        return []
    with open(ANALYZED_FILE, "r") as f:
        return json.load(f)


def load_tracking():
    if not os.path.exists(TRACKING_FILE):
        return {}
    with open(TRACKING_FILE, "r") as f:
        return json.load(f)


def save_tracking(tracking):
    with open(TRACKING_FILE, "w") as f:
        json.dump(tracking, f, indent=2, ensure_ascii=False)


# --- Main App ---

st.title("Heyva Health — Lead Tracking Dashboard")
st.caption(f"Last refreshed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | Click 'Rerun' or refresh page to update")

leads = load_leads()
if not leads:
    st.error("No analyzed leads found. Run the pipeline first.")
    st.stop()

tracking = load_tracking()

# --- Sidebar Filters ---
st.sidebar.header("Filters")

# Priority filter
priorities = sorted(set(l.get("priority_score", 0) for l in leads), reverse=True)
selected_priorities = st.sidebar.multiselect("Priority Score", priorities, default=priorities)

# Status filter
status_options = ["All", "Not Contacted", "Contacted - No Reply", "Contacted - Replied", "Meeting Scheduled", "Not Interested"]
selected_status = st.sidebar.selectbox("Contact Status", status_options)

# Role filter
roles = sorted(set("CFO/Finance" if any(k in l.get("title", "").lower() for k in ["cfo", "finance", "financial"]) else "HR" for l in leads))
selected_roles = st.sidebar.multiselect("Role Type", roles, default=roles)

# --- Apply Filters ---
filtered_leads = []
for lead in leads:
    url = lead.get("linkedin_url", "")
    track = tracking.get(url, {})
    status = track.get("status", "Not Contacted")
    priority = lead.get("priority_score", 0)
    role = "CFO/Finance" if any(k in lead.get("title", "").lower() for k in ["cfo", "finance", "financial"]) else "HR"

    if priority not in selected_priorities:
        continue
    if selected_status != "All" and status != selected_status:
        continue
    if role not in selected_roles:
        continue
    filtered_leads.append(lead)

# --- Summary Metrics ---
total = len(leads)
contacted = sum(1 for l in leads if tracking.get(l.get("linkedin_url", ""), {}).get("status", "Not Contacted") != "Not Contacted")
replied = sum(1 for l in leads if tracking.get(l.get("linkedin_url", ""), {}).get("status", "") == "Contacted - Replied")
meetings = sum(1 for l in leads if tracking.get(l.get("linkedin_url", ""), {}).get("status", "") == "Meeting Scheduled")

col1, col2, col3, col4 = st.columns(4)
col1.metric("Total Leads", total)
col2.metric("Contacted", contacted)
col3.metric("Replied", replied)
col4.metric("Meetings", meetings)

# --- Priority Distribution ---
st.subheader("Priority Distribution")
priority_counts = {}
for l in leads:
    p = l.get("priority_score", 0)
    priority_counts[f"P{p}"] = priority_counts.get(f"P{p}", 0) + 1
priority_df = pd.DataFrame(list(priority_counts.items()), columns=["Priority", "Count"]).sort_values("Priority", ascending=False)
st.bar_chart(priority_df.set_index("Priority"), color="#2D8B2D")

# --- Leads Table ---
st.subheader(f"Leads ({len(filtered_leads)} showing)")

for i, lead in enumerate(sorted(filtered_leads, key=lambda x: x.get("priority_score", 0), reverse=True)):
    url = lead.get("linkedin_url", "")
    track = tracking.get(url, {})
    status = track.get("status", "Not Contacted")
    priority = lead.get("priority_score", 0)

    # Color code by priority
    if priority >= 4:
        priority_color = "🟢"
    elif priority >= 3:
        priority_color = "🟡"
    else:
        priority_color = "🔴"

    # Status indicator
    status_icons = {
        "Not Contacted": "⬜",
        "Contacted - No Reply": "📤",
        "Contacted - Replied": "📩",
        "Meeting Scheduled": "📅",
        "Not Interested": "❌",
    }
    status_icon = status_icons.get(status, "⬜")

    with st.expander(f"{priority_color} P{priority} | {status_icon} {lead.get('name', 'Unknown')} — {lead.get('title', '')[:50]}"):
        col_left, col_right = st.columns([2, 1])

        with col_left:
            st.markdown(f"**Company:** {lead.get('company', 'N/A')}")
            st.markdown(f"**Industry:** {lead.get('industry', 'N/A')}")
            st.markdown(f"**LinkedIn:** [{url}]({url})")
            st.markdown(f"**Priority Reason:** {lead.get('priority_reason', 'N/A')}")

            if lead.get("google_background"):
                st.markdown(f"**Google Background:** {lead.get('google_background', '')}")

            st.markdown("---")
            st.markdown(f"**Tone Profile:** {lead.get('tone_profile', 'N/A')}")

            if lead.get("key_interests"):
                interests = lead.get("key_interests", [])
                if isinstance(interests, list):
                    st.markdown(f"**Key Interests:** {', '.join(interests)}")

            st.markdown("---")
            st.markdown("**Suggested Connection Message:**")
            st.code(lead.get("connection_message", "N/A"), language=None)

            st.markdown("**Suggested Follow-up Message:**")
            st.text_area("", lead.get("followup_message", "N/A"), height=100, key=f"followup_{i}", disabled=True)

            if lead.get("talking_points"):
                st.markdown("**Talking Points:**")
                points = lead.get("talking_points", [])
                if isinstance(points, list):
                    for tp in points:
                        st.markdown(f"- {tp}")

        with col_right:
            st.markdown("### Update Status")

            new_status = st.selectbox(
                "Status",
                ["Not Contacted", "Contacted - No Reply", "Contacted - Replied", "Meeting Scheduled", "Not Interested"],
                index=["Not Contacted", "Contacted - No Reply", "Contacted - Replied", "Meeting Scheduled", "Not Interested"].index(status),
                key=f"status_{i}"
            )

            notes_val = track.get("notes", "")
            new_notes = st.text_area("Notes", notes_val, height=100, key=f"notes_{i}")

            contact_date = track.get("contacted_date", "")
            new_date = st.text_input("Date Contacted", contact_date, key=f"date_{i}", placeholder="YYYY-MM-DD")

            if st.button("Save", key=f"save_{i}"):
                tracking[url] = {
                    "status": new_status,
                    "notes": new_notes,
                    "contacted_date": new_date,
                    "updated_at": datetime.now().isoformat(),
                }
                save_tracking(tracking)
                st.success("Saved!")
                st.rerun()

# --- Export ---
st.sidebar.markdown("---")
st.sidebar.header("Export")
if st.sidebar.button("Export to Excel"):
    rows = []
    for lead in leads:
        url = lead.get("linkedin_url", "")
        track = tracking.get(url, {})
        rows.append({
            "Priority": lead.get("priority_score", 0),
            "Name": lead.get("name", ""),
            "Title": lead.get("title", ""),
            "Company": lead.get("company", ""),
            "Industry": lead.get("industry", ""),
            "LinkedIn URL": url,
            "Status": track.get("status", "Not Contacted"),
            "Date Contacted": track.get("contacted_date", ""),
            "Tone Profile": lead.get("tone_profile", ""),
            "Connection Message": lead.get("connection_message", ""),
            "Follow-up Message": lead.get("followup_message", ""),
            "Key Interests": ", ".join(lead.get("key_interests", [])) if isinstance(lead.get("key_interests"), list) else "",
            "Talking Points": "\n".join(lead.get("talking_points", [])) if isinstance(lead.get("talking_points"), list) else "",
            "Google Background": lead.get("google_background", ""),
            "Priority Reason": lead.get("priority_reason", ""),
            "Notes": track.get("notes", ""),
        })
    df = pd.DataFrame(rows).sort_values("Priority", ascending=False)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output", f"heyva_indonesia_leads_{timestamp}.xlsx")
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    df.to_excel(output_path, index=False)
    st.sidebar.success(f"Exported to {output_path}")
