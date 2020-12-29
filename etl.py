import os
import glob
import psycopg2
import pandas as pd
from sql_queries import *


def process_song_file(cur, filepath):
    """reads a songs file and insert the values into the songs and artists tables"""
    
    # open song file
    df = pd.read_json(filepath, lines = True)

    # insert song record
    song_data = df.get(['song_id', 'title', 'artist_id', 'year', 'duration']).values.tolist()[0]

    try:
        cur.execute(song_table_insert, song_data)
    except (Exception, psycopg2.DatabaseError) as error:
        print(f"Error (songs): %s" % error)

    # insert artist record
    artist_data = df.get(['artist_id', 'artist_name', 'artist_location', 'artist_latitude', 'artist_longitude']).values.tolist()[0]

    try:
        cur.execute(artist_table_insert, artist_data)
    except (Exception, psycopg2.DatabaseError) as error:
        print(f"Error (artists): %s" % error)


def process_log_file(cur, filepath):
    # open log file
    df = pd.read_json(filepath, lines = True)

    # filter by NextSong action
    df = df.query("page == 'NextSong'").reset_index(drop = True)

    # convert timestamp column to datetime
    t = pd.to_datetime(df['ts'])
    
    # insert time data records
    time_data = (df['ts'], t.dt.hour, t.dt.day, t.dt.isocalendar()['week'], t.dt.month, t.dt.year, t.dt.weekday)
    column_labels = ('start_time', 'hour', 'day', 'week', 'month', 'year', 'weekday')
    time_df = pd.DataFrame({col: values for col,values in zip(column_labels, time_data)})

    for i, row in time_df.iterrows():

        try:
            cur.execute(time_table_insert, list(row))
        except (Exception, psycopg2.DatabaseError) as error:
            print(f"Error (time): %s" % error)


    # load user table
    user_df = df.get(['userId', 'firstName', 'lastName', 'gender', 'level']).drop_duplicates()

    # insert user records
    for i, row in user_df.iterrows():

        try:
            cur.execute(user_table_insert, row)
        except (Exception, psycopg2.DatabaseError) as error:
            pass
            #print(f"Error (users): %s" % error)

    # insert songplay records
    for index, row in df.iterrows():
        
        # get songid and artistid from song and artist tables
        cur.execute(song_select, (row.song, row.artist, row.length))
        results = cur.fetchone()
        
        if results:
            print('fount match')
            songid, artistid = results

        else:
            songid, artistid = None, None

        songplay_data = (f'{row.sessionId}_{row.ts}', row.ts, row.userId, row.level, songid, artistid, row.sessionId, row.location, row.userAgent)

        try:
            cur.execute(songplay_table_insert, songplay_data)
        except (Exception, psycopg2.DatabaseError) as error:
            pass
            #print(f"Error (users): %s" % error)


def process_data(cur, conn, filepath, func):
    # get all files matching extension from directory
    all_files = []
    for root, dirs, files in os.walk(filepath):
        files = glob.glob(os.path.join(root,'*.json'))
        for f in files :
            all_files.append(os.path.abspath(f))

    # get total number of files found
    num_files = len(all_files)
    print('{} files found in {}'.format(num_files, filepath))

    # iterate over files and process
    for i, datafile in enumerate(all_files, 1):
        func(cur, datafile)
        conn.commit()
        print('{}/{} files processed.'.format(i, num_files))


def main():
    conn = psycopg2.connect("host=127.0.0.1 dbname=sparkifydb user=student password=student")
    conn.set_session(autocommit=True)
    cur = conn.cursor()

    process_data(cur, conn, filepath='data/song_data', func=process_song_file)
    process_data(cur, conn, filepath='data/log_data', func=process_log_file)

    conn.close()


if __name__ == "__main__":
    main()