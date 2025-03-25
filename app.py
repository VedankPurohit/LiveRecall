import streamlit as st
from Components.Crypt import EncryptDecryptImage
import CaptureStart
import streamlit.components.v1 as components
import numpy as np
import base64, os
#from Components.JsonData import GetPropTime
st.set_page_config(page_title="Recall", page_icon="", layout="wide")


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
            # print(f"Removed file: {file_path}")
    

def get_image(text, NegativeTexts="", NegativeImages = "", PositiveImages = "", NegTextWeight=1.0,NegativeImageWeight = 1.0, PositveImageWeight = 1.0):
    print("Getting Images")
    print(NegativeTexts, NegTextWeight)
    # try:
    if True:
        Emb = CaptureStart.ClipMode.TextEmb(text)
        print("Initial Emb created")
        if SafeMode == True:
            if SafeMode_weight == "Low":
                Negweight = 0.6
            elif SafeMode_weight == "LowMid":
                Negweight = 0.8
            elif SafeMode_weight == "Mid":
                Negweight = 1.0
            elif SafeMode_weight == "MidHigh":
                Negweight = 1.2
            elif SafeMode_weight == "High":
                Negweight = 1.4
            elif SafeMode_weight == "Very High":
                Negweight = 1.8
            elif SafeMode_weight == "Extream":
                Negweight = 2.5
            else:
                Negweight = 0.4
            NegativeTexts = ""
            print(f"Safe mode is on - {text}, {NegativeTexts}, {Negweight}")
            try:
                Emb = CaptureStart.ClipMode.create_query_embedding(Emb= Emb, negative_texts=NegativeTexts,negTextWeight=Negweight, safeMode=True)
            except Exception as e:
                print(f"error - {e} happened in safe mode using create_query_embedding")
        else: 
            print(f"SafeMode is off")
            try:
                Emb = CaptureStart.ClipMode.create_query_embedding(Emb= Emb, negative_texts= NegativeTexts,
                                                                    negative_images=NegativeImages, positive_images= PositiveImages,
                                                                     negTextWeight=NegTextWeight, negImgWeight=NegativeImageWeight, posImgWeight=PositveImageWeight)
            except Exception as e:
                print(f"error - {e} happened in Normal mode using create_query_embedding")
            
        #     print("Extracted Embeddings With Negitives")
        #     Negative = Negative.split(",") # For some reason if i have the final negative mode to be [''], The results are automaticaly safe
        #     print(Negative,Negweight)
        #     for i in range(len(Negative)):
        #         Negative[i] = Negative[i].strip()
        #     Emb = CaptureStart.ClipMode.create_query_embedding([text], Negative,negW=Negweight)
        # print("Extracted Embeddings")
        # print(Negative, Negweight)
        Lis, Scores = CaptureStart.RetriveMemoryMax(Emb,80)
        print(F"Found images {len(Lis)}")
        SavedLis = []
        for a in Lis:
            Save = a.replace("CapturedData", "Temp")
            EncryptDecryptImage(a, CaptureStart.Key, Save)
            SavedLis.append(Save)
        print("Images Got Successfully")
    
        return SavedLis, Scores  
    # except Exception as e:
    #     print("Error in get_image: \n", e)
    #     return []

tab1, tab2, tab3 = st.tabs(["Recall", "Delete", "Settings"])
with tab1:
    st.title("Recall")
    Col1 , Col2, Col3, Col4 = st.columns(4, gap="small")
    with Col1:
        if CaptureStart.Key != "" and st.button("Start", type="secondary") and CaptureStart.Key != "":
            # CaptureStart.ImportModels() ## Loding model only when needed
            CaptureStart.Start = True
            if CaptureStart.Threaded.is_alive() == False:
                CaptureStart.Threaded.start()
        
    with Col2:
        if CaptureStart.Key != "" and st.button("Stop", type="primary"):
            CaptureStart.Start = False
    
    with Col3:
        SafeMode = st.toggle(label="Safe Mode", value=True, key="SafeMode")
        if "prev_safemode_bool" not in st.session_state:
            st.session_state.prev_safemode_bool = True
        # st.write(f"SafeMode is set to : {SafeMode}")

    with Col4:
        SafeMode_weight = st.selectbox(
            "Set Modration Level",
            key="SafeMode_weight",
            options=["Low", "LowMid", "Mid", "MidHigh", "High", "Very High","Extream"],
        )
        if "prev_safemode_weight" not in st.session_state:
            st.session_state.prev_safemode_weight = "Low"

    Col6 , Col7 = st.columns(2, gap="medium")
    with Col6:
        search_term = st.text_input("Search:", key="search_term")  # Use a key for caching
        if 'prev_search_term' not in st.session_state:
            st.session_state.prev_search_term = ""

    with Col7:


        with st.expander("Advanced Settings ⬇️", expanded=False):
            st.markdown("### Customize Additional Options")

            # Positive Images input and weight
            pos_images = st.text_input("Positive Images", 
                                       placeholder="Enter positive image Ids, separated by commas")
            pos_img_weight = st.number_input("Positive Images Weight", min_value=-2.0, max_value= 2.0, value=1.0, step=0.1)

            # Negative Images input and weight
            neg_images = st.text_input("Negative Images", 
                                       placeholder="Enter negative image Ids, separated by commas")
            neg_img_weight = st.number_input("Negative Images Weight", min_value=-2.0, max_value= 2.0, value=1.0, step=0.1)

            # Negative Texts input and weight
            NegativeTerms = st.text_input("Negative Texts", 
                                      placeholder="Enter negative texts, separated by commas")
            neg_text_weight = st.number_input("Negative Texts Weight", min_value=-2.0, max_value= 2.0, value=1.0, step=0.1)
            if "prev_Negative" not in st.session_state:
                st.session_state.prev_Negative = ""


    if CaptureStart.Key != "" and (st.button("Search") or st.session_state.prev_search_term != search_term or st.session_state.prev_Negative != NegativeTerms or st.session_state.prev_safemode_weight != SafeMode_weight):
        # CaptureStart.ImportModels() ## Loading model only when needed
        # After displaying them, remove from Temp
        RemoveImages()
        try:
            if search_term:
                # image_locations, SimiarityScores = get_image(search_term, NegativeTerms, neg_text_weight)
                image_locations, SimiarityScores = get_image(text = search_term, NegativeTexts= NegativeTerms, NegativeImages = neg_images, PositiveImages = pos_images, NegTextWeight=neg_text_weight,NegativeImageWeight = neg_img_weight, PositveImageWeight = pos_img_weight)
                print(len(image_locations))
                if image_locations:
                    try:
                        st.success(f"Found {len(image_locations)} images!")

                        # --- ONLY THIS PART CHANGED FOR IMAGE DISPLAY ---
                        # Create a slider to cycle through the found images
                        if len(image_locations) > 1:
                            selected_index = st.slider(
                                "Slide to view images",
                                min_value=0,
                                max_value=len(image_locations) - 1,
                                value=0,
                                help="Move the slider to switch between images."
                            )
                        else:
                            selected_index = 0

                        # Show the selected image
                        st.image(
                            image_locations[selected_index],
                            use_column_width=True
                        )

                        # Optionally, show a caption
                        st.caption(f"Image {selected_index + 1} of {len(image_locations)}")

                        st.header("Gallery")
                        col1, col2, col3 = st.columns(3, gap="medium")
                        with st.container():
                            for i, image_location in enumerate(image_locations):
                                with col1 if i % 3 == 0 else col2 if i % 3 == 1 else col3:
                                    # st.image(image_location,caption=f"Score - {SimiarityScores[i]} ")
                                    st.image(image_location,caption=image_location.replace("Temp\screenshot_","").replace(".png","").replace(".jpg", "").replace("Temp\Snap -", ""), use_column_width  = "auto")
                    except:
                        st.warning("No images found for your search term.")



                else:
                    st.warning("No images found for your search term.")
            else:
                st.warning("Please enter a search term.")
        except:
            st.warning("No images found for your search term. Or some Error occurred, I'm not too sure")

with tab2:
    st.title("Delete")
    st.write("comming soon...")

with tab3:
    st.title("Settings")
    SafeMode_weight = st.slider(
        "Slide to set SafeMode Weight",
        min_value=-1.0,
        max_value=2.5,
        value=0.8,
        help="Move the slider to change SafeMode Weight.",
        step=0.05
    )


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

