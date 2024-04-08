#Project-1
Youtube Data Harvesting and Warehousing


import mysql.connector
import os
import googleapiclient.discovery
from googleapiclient.errors import HttpError
import json
import pandas as pd
import streamlit as st
import requests_cache
import matplotlib.pyplot as plt
import seaborn as sns



#  UCeHd7SV9Cqa6s7awp9t3CcQ -As pubg
# UCj0VBmldP8Hans-KYYxpAAA
# UCduIoIMfD8tT3KoU0-zBRgQ
# UCxJQSw2xdA-8EbZmj9XKZ_A
# UCLzw8opUlMnSA2TQfj34K9w


def Api():
    api = "AIzaSyClhjTeoUtn5P2K9nu-7ziMtgm-V7Dimh8"
    api_service_name = "youtube"
    api_version = "v3"


    requests_cache.install_cache('youtube_api_cache', backend='sqlite', expire_after=3600)  

    youtube = googleapiclient.discovery.build(
        api_service_name, api_version, developerKey=api)
    return youtube

youtube = Api()



mydb=mysql.connector.connect(
 host='localhost',
 user='root',
 password='root',
 database='youtube')

cursor = mydb.cursor()


def channel_info(id):
    cursor.execute("""CREATE TABLE IF NOT EXISTS channel_info (
                        channel_Name VARCHAR(255),
                        channel_Id VARCHAR(255),
                        subscribe INT,
                        views INT,
                        Total_videos INT,
                        channel_description TEXT,
                        Playlist_id VARCHAR(255)
                    )""")
    
    request = youtube.channels().list(
        part="snippet,contentDetails,statistics",
        id=id)
    response = request.execute()

    for i in response.get('items', []):
        data = dict(channel_Name=i['snippet']['title'],
                    channel_Id=i['id'],
                    subscribe=i['statistics']['subscriberCount'],
                    views=i['statistics']['viewCount'],
                    Total_videos=i['statistics']['videoCount'],
                    channel_description=i['snippet']['description'],
                    Playlist_id=i['contentDetails']['relatedPlaylists']['uploads'])
        
        try:
            channel_Id = data['channel_Id']
            cursor.execute("SELECT * FROM channel_info WHERE channel_Id = %s", (channel_Id,))
            result = cursor.fetchone()

            if not result:
                sql = """INSERT INTO channel_info (channel_Name, channel_Id, subscribe, views, Total_videos, channel_description, Playlist_id) 
                         VALUES (%s, %s, %s, %s, %s, %s, %s)"""
                values = (data['channel_Name'], data['channel_Id'], data['subscribe'], data['views'], data['Total_videos'], data['channel_description'], data['Playlist_id'])
                cursor.execute(sql, values)
                st.success("Data inserted successfully!")
            else:
                st.warning("Record already exists in the table")
        except mysql.connector.Error as error:
            print("Failed to insert record into channel_info table {}".format(error))

    mydb.commit()

    return data


def get_Videos_Ids(channel_id):
    Video_Ids=[]
    
    response=youtube.channels().list(id=channel_id,
                                    part='contentDetails').execute()
    Playlist_Id=response['items'][0]['contentDetails']['relatedPlaylists']['uploads']
    
    next_page_token=None
    
    while True:
        response1=youtube.playlistItems().list(
                                        part='snippet',
                                        playlistId=Playlist_Id,
                                        maxResults=50,
                                        pageToken=next_page_token).execute()
        for i in range(len(response1['items'])):
            Video_Ids.append(response1['items'][i]['snippet']['resourceId']['videoId'])
        next_page_token=response1.get('nextPageToken')
        if next_page_token is None:
            break
            
    cursor.execute("""CREATE TABLE IF NOT EXISTS video_ids (
                        video_id VARCHAR(255)
                    )""")
    
    # Insert data into MySQL
    for video_id in Video_Ids:
        cursor.execute("INSERT INTO video_ids (video_id) VALUES (%s)", (video_id,))
    
  

    mydb.commit()
    return Video_Ids 
    


#get video information
def get_video_info(Video_Ids):
    video_data=[]
    for video_id in Video_Ids:
        request=youtube.videos().list(
        part="snippet,contentDetails,statistics",
        id=video_id
        )
        response=request.execute()
        
        cursor.execute("""CREATE TABLE IF NOT EXISTS video_info (
                            channel_Name VARCHAR(255),
                            channel_Id VARCHAR(255),
                            video_Id VARCHAR(255),
                            Title VARCHAR(255),
                            Tags TEXT,
                            Thumbnail TEXT,
                            Description TEXT,
                            Published_data VARCHAR(255),
                            Duration VARCHAR(255),
                            view INT,
                            likes INT,
                            dislikes INT,
                            comments INT
                        )""")

        for item in response["items"]:
            data=dict(channel_Name=item['snippet']['channelTitle'],
                     channel_Id=item['snippet']['channelId'],
                     video_Id=item['id'],
                     Title=item['snippet']['title'],
                     Tags=json.dumps(item.get('tags')),
                     Thumbnail=json.dumps(item['snippet']['thumbnails']),
                     Description=item['snippet'].get('description'),
                     Published_data=item['snippet']['publishedAt'].replace('T', ' ').replace('Z', ''),
                     Duration=item['contentDetails']['duration'],
                     view=item['statistics'].get('viewCount'),
                     likes=item['statistics'].get('likeCount'),
                     dislikes=item['statistics'].get('dislikeCount'),
                     comments=item['statistics'].get('commentCount')
                     )
            video_data.append(data)

            # Insert data into MySQL
            cursor.execute("INSERT INTO video_info (channel_Name, channel_Id, video_Id, Title, Tags, Thumbnail, Description, Published_data, Duration, view, likes, dislikes, comments) VALUES ( %s, %s, %s,%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
                           (data['channel_Name'], data['channel_Id'], data['video_Id'], data['Title'], data['Tags'], data['Thumbnail'], data['Description'], data['Published_data'], data['Duration'], data['view'], data['likes'], data['dislikes'], data['comments']))
            mydb.commit()

    return video_data




#get comment

def get_comment_info(video_ids):
    comment_data=[]
    try:
        cursor.execute("""CREATE TABLE IF NOT EXISTS comment_info (
                            comment_Id VARCHAR(255),
                            video_Id VARCHAR(255),
                            comment_Text TEXT,
                            comment_Author VARCHAR(255),
                            comment_Published VARCHAR(255)
                        )""")
        
        for video_id in video_ids:
            request=youtube.commentThreads().list(
            part='snippet',
            videoId=video_id,
            maxResults=50
            )
            response=request.execute()

            for item in response['items']:
                data=dict(comment_Id=item['snippet']['topLevelComment']['id'],
                         video_Id=item['snippet']['topLevelComment']['snippet']['videoId'],
                         comment_Text=item['snippet']['topLevelComment']['snippet']['textDisplay'],
                         comment_Author=item['snippet']['topLevelComment']['snippet']['authorDisplayName'],
                         comment_Published=item['snippet']['topLevelComment']['snippet']['publishedAt'].replace('T', ' ').replace('Z', ''))

                comment_data.append(data)

                # Insert data into MySQL
                cursor.execute("INSERT INTO comment_info (comment_Id, video_Id, comment_Text, comment_Author, comment_Published) VALUES (%s, %s, %s, %s, %s)",
                               (data['comment_Id'], data['video_Id'], data['comment_Text'], data['comment_Author'], data['comment_Published']))
                mydb.commit()
    except Exception as e:
        error_message = e.content.decode('utf-8')
        if 'commentsDisabled' in error_message:
            print("Comments are disabled for this video.")
            return []
        else:
            print("An error occurred:", error_message)
            return None
    
    return comment_data





#get playlist 

def get_playlist_details(channel_id):
    All_data=[]
    try:
        cursor.execute("""CREATE TABLE IF NOT EXISTS playlist_details(
                            Playlist_Id VARCHAR(255),
                            channel_Name VARCHAR(255),
                            channel_Id VARCHAR(255),
                            video_Id VARCHAR(255),
                            Title VARCHAR(255),
                            Published_data VARCHAR(255),
                            video_count INT
                        )""")
        request=youtube.playlists().list(
            part="snippet,contentDetails",
            channelId=channel_id,
            maxResults=50
        )
        response=request.execute()

        for item in response['items']:
            Playlist_Id=item['id']
            Title=item['snippet']['title']
            Published_data=item['snippet']['publishedAt'].replace('T', ' ').replace('Z', '')
            video_count=item['contentDetails']['itemCount']

            # Fetch video IDs in the playlist
            video_ids = []
            next_page_token = None
            while True:
                playlist_items_request = youtube.playlistItems().list(
                    part="snippet",
                    playlistId=Playlist_Id,
                    maxResults=50,
                    pageToken=next_page_token
                )
                playlist_items_response = playlist_items_request.execute()

                for playlist_item in playlist_items_response["items"]:
                    video_ids.append(playlist_item["snippet"]["resourceId"]["videoId"])

                next_page_token = playlist_items_response.get("nextPageToken")
                if not next_page_token:
                    break

            for video_id in video_ids:
                data=dict(Playlist_Id=Playlist_Id,
                          channel_Name=item['snippet']['channelTitle'],
                          channel_Id=channel_id,
                          video_Id=video_id,
                          Title=Title,
                          Published_data=Published_data,
                          video_count=video_count)
                All_data.append(data)

                # Insert data into MySQL
                cursor.execute("INSERT INTO playlist_details (Playlist_Id, channel_Name, channel_Id, video_Id, Title, Published_data, video_count) VALUES (%s, %s, %s, %s, %s, %s, %s)",
                               (data['Playlist_Id'], data['channel_Name'], data['channel_Id'], data['video_Id'], data['Title'], data['Published_data'], data['video_count']))
                mydb.commit()
    except Exception as e:
        print(f"Error: {e}")
    
    return All_data





def video(Video_Ids):
    video_get=[]
    for video_id in Video_Ids:
        request=youtube.videos().list(
        part="snippet,contentDetails,statistics",
        id=video_id
        )
        response=request.execute()
        
        cursor.execute("""CREATE TABLE IF NOT EXISTS videos (
                    channel_Name VARCHAR(255),
                    channel_Id VARCHAR(255),
                    video_Id VARCHAR(255),
                    Title VARCHAR(255),
                    Tags TEXT,
                    Thumbnail TEXT,
                    Description TEXT,
                    Published_date VARCHAR(255),
                    Duration VARCHAR(255),
                    view INT,
                    likes INT,
                    dislikes INT,
                    comments INT
                )""")

       
        for item in response["items"]:
            data=dict(channel_Name=item['snippet']['channelTitle'],
                     channel_Id=item['snippet']['channelId'],
                     video_Id=item['id'],
                     Title=item['snippet']['title'],
                     Tags=json.dumps(item.get('tags')),
                     Thumbnail=json.dumps(item['snippet']['thumbnails']),
                     Description=item['snippet'].get('description'),
                     Published_date=item['snippet']['publishedAt'].replace('T', ' ').replace('Z', ''),
                     Duration=item['contentDetails']['duration'],
                     view=item['statistics'].get('viewCount'),
                     likes=item['statistics'].get('likeCount'),
                     dislikes=item['statistics'].get('dislikeCount'),
                     comments=item['statistics'].get('commentCount')
                     )
            video_get.append(data)

            # Insert data into MySQL
            cursor.execute("INSERT INTO videos (channel_Name, channel_Id, video_Id, Title, Tags, Thumbnail, Description, Published_date, Duration, view, likes, dislikes, comments) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
               (data['channel_Name'], data['channel_Id'], data['video_Id'], data['Title'], data['Tags'], data['Thumbnail'], data['Description'], data['Published_date'], data['Duration'], data['view'], data['likes'], data['dislikes'], data['comments']))

            mydb.commit()

    return video_get




def get_channel_details(channel_id):
    channel_details = channel_info(channel_id)
    Video_Ids = get_Videos_Ids(channel_id)
    video_details = get_video_info(Video_Ids)
    comment_details = get_comment_info(Video_Ids)
    playlist_details = get_playlist_details(channel_id)
    video_details = video(Video_Ids)
    
    # Convert dictionaries to DataFrames
    channel_df = pd.DataFrame([channel_details])
    video_df = pd.DataFrame(video_details)
    comment_df = pd.DataFrame(comment_details)
    playlist_df = pd.DataFrame(playlist_details)
    video_detail_df = pd.DataFrame(video_details)
    
    return {
        "channel_details": channel_df,
        "video_details": video_df,
        "comment_details": comment_df,
        "playlist_details": playlist_df,
        "video_data": video_detail_df
    }
    

def main():
    st.sidebar.title("Navigation")
    option = st.sidebar.radio("Select an option", ["Home", "Channel Details", "Go to Question"])

    if option == "Home":
        st.title(":blue[YOUTUBE DATA HAVERSTING AND WAREHOUSING]")
    elif option == "Channel Details":
        st.title('YouTube Channel Details')
        channel_id = st.text_input('Enter YouTube Channel ID:')
        if st.button('Get Channel Details'):
            details = get_channel_details(channel_id)
            st.subheader('Channel Details')
            st.write(details["channel_details"])

            st.subheader('Video Details')
            st.write(details["video_details"])

            st.subheader('Comment Details')
            st.write(details["comment_details"])

            st.subheader('Playlist Details')
            st.write(details["playlist_details"])
    elif option == "Go to Question":
        st.session_state.page = 'questions_page'
        
def questions_page():
    questions = [
        "Names of all the videos and their corresponding channels",
        "Channels with the most number of videos and how many videos they have",
        "Top 10 most viewed videos and their respective channels",
        "Number of comments for each video and their corresponding video names",
        "Videos with the highest number of likes and their corresponding channel names",
        "Total number of likes and dislikes for each video and their corresponding video names",
        "Total number of views for each channel and their corresponding channel names",
        "Names of all the channels that have published videos in the year 2022",
        "Average duration of all videos in each channel and their corresponding channel names",
        "Videos with the highest number of comments and their corresponding channel names"
    ]

    selected_question = st.selectbox("Select a question", questions, key="selectbox_unique_key")

    # Fetch data based on the selected question
    if st.button('Submit'):
        if selected_question == questions[0]:
            cursor.execute("SELECT  Title, channel_name FROM videos")
            data = cursor.fetchall()
            df = pd.DataFrame(data, columns=['video Title','Channel_Name'])
            st.write(df)


        elif selected_question == questions[1]:
            cursor.execute("SELECT channel_name, COUNT(*) as video_count FROM videos GROUP BY channel_name ORDER BY video_count DESC")
            data = cursor.fetchall()
            df = pd.DataFrame(data, columns=['Channel_Name', 'No of videos'])
            st.write(df)

            # Create a bar chart using Matplotlib

            fig, ax = plt.subplots()
            plt.bar(df['Channel_Name'], df['No of videos'])
            plt.xlabel('Channel_Name')
            plt.ylabel('No of videos')
            plt.title('No of videos by channel')
            plt.xticks(rotation=45, ha='right', fontsize=8)
            st.pyplot(fig)



        elif selected_question == questions[2]:
            cursor.execute("SELECT Title, channel_name, view FROM videos ORDER BY view DESC LIMIT 10")
            data = cursor.fetchall()
            df = pd.DataFrame(data, columns=['Video_Title', 'Channel name','View Count'])
            st.write(df)

            # Create a bar chart using Matplotlib
             
            fig, ax = plt.subplots()
            plt.bar(df['Video_Title'], df['View Count'])
            plt.xlabel('Video_Title')
            plt.ylabel('View Count')
            plt.title('Top 10 Videos by Views')
            plt.xticks(rotation=50, ha='right', fontsize=8)
            st.pyplot(fig)


        elif selected_question == questions[3]:
            cursor.execute("SELECT Title, COUNT(*) as comments FROM videos GROUP BY Title")
            data = cursor.fetchall()
            df = pd.DataFrame(data, columns=['Video Title', 'No of comments'])
            st.write(df)


        elif selected_question == questions[4]:
            cursor.execute("SELECT MAX(likes) as max_likes FROM videos")
            data = cursor.fetchall()
            df = pd.DataFrame(data, columns=['Highest Likes'])
            st.write(df)

            # Create a bar chart using Matplotlib

            fig, ax = plt.subplots()
            plt.bar(df['Highest Likes'], df['Highest Likes'], color= 'green')
            plt.xlabel('Video Title')
            plt.ylabel('No of comments')
            plt.title('Highest Number of Likes for a Video')
            st.pyplot(fig)

        elif selected_question == questions[5]:
            cursor.execute("SELECT Title, SUM(likes) as total_likes, SUM(dislikes) as total_dislikes FROM videos GROUP BY Title")
            data = cursor.fetchall()
            df = pd.DataFrame(data, columns=['Video Title','Like Count','Dislike Count'])
            st.write(df)

        # Create a grouped bar chart using Matplotlib

            fig, ax = plt.subplots()
            width = 0.35  # the width of the bars
            ind = range(len(df))  # the x locations for the groups
            ax.bar(ind, df['Like Count'], width, label='Likes Count', color='blue')
            ax.bar(ind, df['Dislike Count'], width, bottom=df['Dislike Count'], label='Dislikes', color='green')
            ax.set_xlabel('Video Title')
            ax.set_ylabel('Count')
            ax.set_title('Likes and Dislikes per Video')
            ax.legend()
            st.pyplot(fig)

        elif selected_question == questions[6]:
            cursor.execute("SELECT channel_name, SUM(view) as total_views FROM videos GROUP BY channel_name")
            data = cursor.fetchall()
            df = pd.DataFrame(data, columns=['Channel Name', 'No of views'])
            st.write(df)

            # Create a bar chart using Matplotlib

            fig, ax = plt.subplots()
            plt.bar(df['Channel Name'],df['No of views'], color= 'blue')
            plt.xlabel('Channel Name')
            plt.ylabel('No of views')
            plt.title('Total Views per channel')
            plt.xticks(rotation=45, ha='right', fontsize=8)
            plt.tight_layout()
            st.pyplot(fig)

        elif selected_question == questions[7]:
            cursor.execute("SELECT DISTINCT channel_name FROM videos WHERE YEAR(published_date) = 2022")
            data = cursor.fetchall()
            df = pd.DataFrame(data, columns=['Channel Name'])
            st.write(df)

            # Count the number of unique channels
            num_channels = len(df)
            
            # Create a horizontal bar chart using Matplotlib
            fig, ax = plt.subplots(figsize=(8, num_channels * 0.5))  # Adjust height based on the number of channels
            ax.barh(df['Channel Name'], 1, color='skyblue')  # Bar width set to 1
            ax.set_xlabel('Count')
            ax.set_ylabel('Channel Name')
            ax.set_title('Unique Channels in 2022')
            st.pyplot(fig)
            

        elif selected_question == questions[8]:
            cursor.execute("""SELECT channel_name, AVG(duration_minutes) AS avg_duration 
                        FROM (
                                SELECT channel_name, TIME_TO_SEC(SUBSTRING(duration, 3)) / 60 AS duration_minutes 
                                FROM videos
                            ) AS durations 
                            GROUP BY channel_name """)
            data = cursor.fetchall()
            df = pd.DataFrame(data, columns=['Channel Name', 'Average Sec'])
            st.write(df)
            
            # Create a vertical bar chart using Matplotlib
            
            fig, ax = plt.subplots(figsize=(10, 6))  # Set figure size (width, height)
            ax.bar(df['Channel Name'], df['Average Sec'], color='skyblue')
            ax.set_xlabel('Channel Name')
            ax.set_ylabel('Average Sec')
            ax.set_title('Average Duration of Videos per Channel')
            plt.xticks(rotation=45, ha='right', fontsize=8)  # Rotate x-axis labels and adjust fontsize
            plt.tight_layout()  # Adjust layout to prevent overlapping labels
            st.pyplot(fig)

        
        elif selected_question == questions[9]:
            cursor.execute("""SELECT v.video_Id, v.Title, v.channel_Name, v.comments
                    FROM (
                        SELECT *,
                            ROW_NUMBER() OVER (PARTITION BY v.channel_id ORDER BY v.comments DESC) AS row_num
                        FROM Videos v
                    ) v
                    JOIN channel_info c ON v.channel_Id = c.channel_Id
                    WHERE v.row_num = 1
                           """)
            
            data = cursor.fetchall()
            df = pd.DataFrame(data, columns=['Video Id', 'Title', 'Channel Name', 'No of Counts'])
            st.write(df)

            # Create a bar chart using Matplotlib
            fig, ax = plt.subplots(figsize=(8, 6))
            ax.bar(df['Channel Name'], df['No of Counts'], color='skyblue')
            ax.set_xlabel('Channel Name')
            ax.set_ylabel('No of Counts')
            ax.set_title('Comment Count for Video with Most Comments')
            plt.xticks(rotation=45, ha='right', fontsize=8)
            plt.tight_layout()
            st.pyplot(fig)

        data = cursor.fetchall()
        df = pd.DataFrame()
        st.write()
    
    
    if st.button('Go to Home Page'):
        st.session_state.page = 'main_page'


if __name__ == '__main__':
        if 'page' not in st.session_state:
            st.session_state.page = 'main_page'

        if st.session_state.page == 'main_page':
            main()
        elif st.session_state.page == 'questions_page':
            questions_page()

mydb.close()
