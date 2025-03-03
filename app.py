import streamlit as st
from Components.Crypt import EncryptDecryptImage
import CaptureStart
import os
#from Components.JsonData import GetPropTime
st.set_page_config(page_title="Recall", page_icon="")


with st.popover("Enter Your Key"):
    st.markdown("Enter a Valid Key")
    CaptureStart.Key = st.text_input("What's your Key?")
    if CaptureStart.Key == "DevMode":
        st.warning("DevMode Activated, No Security")
    elif CaptureStart.Key == "":
        st.warning("Please Enter a Valid Key")
    else:
        st.success("Security Activated, Encription On")


def RemoveImages(directory= "Temp"):
    files = os.listdir(directory)
    
    for file in files:
        file_path = os.path.join(directory, file)
        if os.path.isfile(file_path):
            os.remove(file_path)
            print(f"Removed file: {file_path}")
    

def get_image(text):
    print("Getting Images")
    try:

        Emb = CaptureStart.ClipMode.TextEmb(text)
        Lis, _ = CaptureStart.RetriveMemoryMax(Emb,6)
        SavedLis = []
        for a in Lis:
            Save = a.replace("CapturedData", "Temp")
            EncryptDecryptImage(a, CaptureStart.Key, Save)
            SavedLis.append(Save)
        print("Images Got Successfully")
    
        return SavedLis
    except:
        return []

tab1, tab2, tab3 = st.tabs(["Recall", "Delete", "Settings"])
with tab1:
    st.title("Recall")
    Col1 , Col2 = st.columns(2, gap="small")
    with Col1:
        if CaptureStart.Key != "" and st.button("Start", type="secondary") and CaptureStart.Key != "":
            CaptureStart.Start = True
            if CaptureStart.Threaded.is_alive() == False:
                CaptureStart.Threaded.start()
        
    with Col2:
        if CaptureStart.Key != "" and st.button("Stop", type="primary"):
            CaptureStart.Start = False


    search_term = st.text_input("Search:", key="search_term")  # Use a key for caching
    if 'prev_search_term' not in st.session_state:
        st.session_state.prev_search_term = ""

    if CaptureStart.Key != "" and (st.button("Search") or st.session_state.prev_search_term != search_term):
        try:
            if search_term:
                image_locations = get_image(search_term)
                if image_locations:
                    st.success(f"Found {len(image_locations)} images!")
    
                    col1, col2, col3 = st.columns(3, gap="medium")
                    with st.container():
                        for i, image_location in enumerate(image_locations):
                            with col1 if i % 3 == 0 else col2 if i % 3 == 1 else col3:
                                st.image(image_location,caption=image_location.replace("Temp\screenshot_","").replace(".png","").replace(".jpg", ""), use_column_width  = "auto")
                    RemoveImages()
    
                    
                else:
                    st.warning("No images found for your search term.")
            else:
                st.warning("Please enter a search term.")
        except:
            st.warning("No images found for your search term. Or some Error occured, Im not too sure")
with tab2:
    st.title("Delete")
    st.write("comming soon...")

with tab3:
    st.title("Settings")
    mode_descriptions = {
        "Normal": "Balanced settings for everyday use",
        "Games": "Less frequent captures for gaming sessions",
        "Slow": "Less frequent captures for gaming sessions",
        "Remember": "Higher sensitivity to capture more details",
        "Fast": "Higher sensitivity to capture more details",
        "Presentation": "Optimized for slide decks and presentations",
        "Video": "Captures key scenes and transitions in videos",
        "Coding": "Tracks meaningful changes in code editors",
        "Security": "Minimizes false triggers for surveillance",
        "Timelapse": "Regular interval captures regardless of content"
    }
    
    option = st.selectbox(
    "Select Capture Mode",
    ("Normal", "Slow", "Fast", "Games", "Remember", "Presentation", "Video", "Coding", "Security", "Timelapse"),
)   
    if option:
        CaptureStart.CaptureMode(option)
        st.write(f"You selected: {option} : {mode_descriptions[option]}")
    st.write("Settings are comming soon...")

