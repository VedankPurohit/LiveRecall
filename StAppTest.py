import streamlit as st

st.title("My App")

# Create an expander for advanced settings
with st.expander("Advanced Settings ⬇️", expanded=False):
    st.markdown("### Customize Additional Options")
    
    # Positive Images input and weight
    pos_images = st.text_input("Positive Images", 
                               placeholder="Enter positive image URLs or descriptions, separated by commas")
    pos_weight = st.number_input("Positive Images Weight", min_value=0.0, value=1.0, step=0.1)
    
    # Negative Images input and weight
    neg_images = st.text_input("Negative Images", 
                               placeholder="Enter negative image URLs or descriptions, separated by commas")
    neg_img_weight = st.number_input("Negative Images Weight", min_value=0.0, value=1.0, step=0.1)
    
    # Negative Texts input and weight
    neg_texts = st.text_input("Negative Texts", 
                              placeholder="Enter negative texts, separated by commas")
    neg_text_weight = st.number_input("Negative Texts Weight", min_value=0.0, value=1.0, step=0.1)

# Example use: Show the entered values
st.write("Positive Images:", pos_images, "with weight", pos_weight)
st.write("Negative Images:", neg_images, "with weight", neg_img_weight)
st.write("Negative Texts:", neg_texts, "with weight", neg_text_weight)
