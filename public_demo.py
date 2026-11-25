import pandas as pd
import streamlit as st

st.set_page_config(
    page_title="Customer Support Call Analysis Demo",
    page_icon="📞",
    layout="wide",
)

st.title("Customer Support Call Analysis")
st.caption("Public demo · synthetic data only")
st.warning(
    "This public preview uses fictional sample data. Audio uploads, transcript processing, "
    "and Gemini API access are disabled."
)

metrics = st.columns(4)
metrics[0].metric("Calls analyzed", "128")
metrics[1].metric("First-call resolution", "72.7%")
metrics[2].metric("Customer satisfaction", "81.2%")
metrics[3].metric("Calls needing review", "14")

left, right = st.columns(2)
with left:
    st.subheader("Synthetic call topics")
    st.bar_chart(
        pd.DataFrame(
            {"Calls": [38, 31, 24, 19, 16]},
            index=[
                "Billing or payment",
                "Delivery or order status",
                "Account access",
                "Technical issue",
                "Other",
            ],
        )
    )

with right:
    st.subheader("Synthetic sentiment")
    st.bar_chart(
        pd.DataFrame(
            {"Calls": [71, 39, 18]},
            index=["Satisfied", "Neutral", "Frustrated"],
        )
    )

st.subheader("Sample call review")
st.dataframe(
    pd.DataFrame(
        [
            {
                "Call": "DEMO-001",
                "Topic": "Billing or payment",
                "Sentiment": "Frustrated",
                "Resolution": "Partly resolved",
                "Language": "English",
            },
            {
                "Call": "DEMO-002",
                "Topic": "Delivery or order status",
                "Sentiment": "Satisfied",
                "Resolution": "Resolved",
                "Language": "Hindi",
            },
            {
                "Call": "DEMO-003",
                "Topic": "Account access",
                "Sentiment": "Neutral",
                "Resolution": "Resolved",
                "Language": "Hinglish",
            },
        ]
    ),
    hide_index=True,
    use_container_width=True,
)

with st.expander("Fictional transcript excerpt"):
    st.write(
        "Customer: I would like to check the status of my recent order.\n\n"
        "Support agent: I can help with that. Your order is scheduled to arrive tomorrow."
    )
    st.caption("Illustrative text only; it is not from a real customer call.")
