import streamlit as st
import pandas as pd
import mysql.connector
import datetime

# --- DATABASE CONFIGURATION ---
DB_CONFIG = {
    "host": "localhost",
    "user": "root",
    "password": "", # Change if you have a MySQL password
    "database": "GYM"
}

@st.cache_resource
def get_connection():
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        return conn
    except mysql.connector.Error as err:
        st.error(f"Error connecting to database: {err}")
        return None

def run_query(query, params=None, fetch=True):
    conn = get_connection()
    if conn:
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute(query, params or ())
            if fetch:
                result = cursor.fetchall()
            else:
                conn.commit()
                result = True
            cursor.close()
            return result
        except mysql.connector.Error as err:
            st.error(f"Database Error: {err}")
            cursor.close()
            return None

# --- MAIN APP LAYOUT & NAVIGATION ---
st.set_page_config(page_title="Gym Management System", layout="wide")

st.sidebar.title("Navigation")
pages = ["Homepage", "View Courses", "View Instructors", "Add Course", "Add Lesson"]
selection = st.sidebar.radio("Go to page:", pages)

# --- PAGE 1: HOMEPAGE ---
if selection == "Homepage":
    st.title("Welcome to the Gym Management System")
    st.markdown("""
    This Streamlit application allows users to explore and manage the daily operations of our Gym. 
    **Objective:** Provide an interactive dashboard to visualize scheduled lessons, manage course offerings, and organize instructor assignments.
    
    *Student Name: [Insert Your Name Here]*
    """)
    
    st.divider()
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Lessons per Time Slot")
        query_time = "SELECT StartTime, COUNT(*) as NumLessons FROM PROGRAM GROUP BY StartTime"
        data_time = run_query(query_time)
        if data_time:
            df_time = pd.DataFrame(data_time)
            # Formatting StartTime for display
            df_time['StartTime'] = df_time['StartTime'].astype(str)
            st.area_chart(df_time.set_index("StartTime"))
            
    with col2:
        st.subheader("Lessons per Day")
        query_day = "SELECT Day, COUNT(*) as NumLessons FROM PROGRAM GROUP BY Day"
        data_day = run_query(query_day)
        if data_day:
            df_day = pd.DataFrame(data_day)
            # Sorting days logically
            sorter = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
            df_day['Day'] = pd.Categorical(df_day['Day'], categories=sorter, ordered=True)
            df_day = df_day.sort_values('Day')
            st.bar_chart(df_day.set_index("Day"))

# --- PAGE 2: VIEW COURSES ---
elif selection == "View Courses":
    st.title("Available Courses")
    
    # Metrics
    courses_data = run_query("SELECT COUNT(*) as Total, COUNT(DISTINCT CType) as DistinctTypes FROM COURSES")
    if courses_data:
        col1, col2 = st.columns(2)
        col1.metric("Total Courses", courses_data[0]["Total"])
        col2.metric("Distinct Types", courses_data[0]["DistinctTypes"])
        
    st.divider()
    
    # Filters
    types_data = run_query("SELECT DISTINCT CType FROM COURSES")
    if types_data:
        available_types = [t['CType'] for t in types_data]
        selected_types = st.multiselect("Filter by Course Type:", available_types, default=available_types)
        
        levels_data = run_query("SELECT MIN(Level) as MinLvl, MAX(Level) as MaxLvl FROM COURSES")
        min_lvl = levels_data[0]['MinLvl'] or 1
        max_lvl = levels_data[0]['MaxLvl'] or 4
        
        selected_levels = st.slider("Select Level Range:", min_value=int(min_lvl), max_value=int(max_lvl), value=(int(min_lvl), int(max_lvl)))
        
        if selected_types:
            format_strings = ','.join(['%s'] * len(selected_types))
            query = f"SELECT * FROM COURSES WHERE CType IN ({format_strings}) AND Level BETWEEN %s AND %s"
            params = tuple(selected_types) + (selected_levels[0], selected_levels[1])
            
            filtered_courses = run_query(query, params)
            
            if filtered_courses:
                df_courses = pd.DataFrame(filtered_courses)
                st.dataframe(df_courses, use_container_width=True)
                
                # Expander for lesson plans
                with st.expander("View Lesson Plans for Selected Courses"):
                    codcs = df_courses['CodC'].tolist()
                    if codcs:
                        format_codc = ','.join(['%s'] * len(codcs))
                        plan_query = f"""
                            SELECT P.CodC, P.Day, P.StartTime, P.Duration, P.Room, 
                                   CONCAT(I.Name, ' ', I.Surname) AS InstructorName, I.Email 
                            FROM PROGRAM P 
                            JOIN INSTRUCTOR I ON P.FisCode = I.FisCode 
                            WHERE P.CodC IN ({format_codc})
                        """
                        plans = run_query(plan_query, tuple(codcs))
                        if plans:
                            st.dataframe(pd.DataFrame(plans), use_container_width=True)
                        else:
                            st.warning("No scheduled lessons found for the selected courses.")
            else:
                st.warning("No courses found matching the selected criteria.")
        else:
            st.error("Please select at least one Course Type.")

# --- PAGE 3: VIEW INSTRUCTORS ---
elif selection == "View Instructors":
    st.title("Instructors Directory")
    
    col1, col2 = st.columns(2)
    with col1:
        search_surname = st.text_input("Filter by Surname (Leave empty for all):", "")
    with col2:
        # Default dates to cover a wide range
        date_range = st.date_input("Filter by Date of Birth Range:", 
                                   value=(datetime.date(1950, 1, 1), datetime.date(2005, 12, 31)))
        
    if len(date_range) == 2:
        start_date, end_date = date_range
        
        query = "SELECT * FROM INSTRUCTOR WHERE BirthDate BETWEEN %s AND %s"
        params = [start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d')]
        
        if search_surname:
            query += " AND Surname LIKE %s"
            params.append(f"%{search_surname}%")
            
        instructors = run_query(query, tuple(params))
        
        if instructors:
            df_inst = pd.DataFrame(instructors)
            
            # Element by element rendering
            for index, row in df_inst.iterrows():
                with st.container():
                    col_icon, col_info = st.columns([1, 11])
                    with col_icon:
                        st.markdown("🧑‍🏫") 
                    with col_info:
                        st.markdown(f"**{row['Name']} {row['Surname']}**")
                        st.markdown(f"**Fiscal Code:** {row['FisCode']} | **Birth Date:** {row['BirthDate']}")
                        st.markdown(f"**Contact:** {row['Email']} | **Phone:** {row['Telephone']}")
                    st.divider()
        else:
            st.warning("No instructors found matching the criteria.")
    else:
        st.info("Please select a complete start and end date.")

# --- PAGE 4: ADD COURSE ---
elif selection == "Add Course":
    st.title("Insert New Course")
    st.markdown("Use this form to add a new course to the catalog. Ensure the code begins with 'CT' and the level is between 1 and 4.")
    
    with st.form("add_course_form"):
        col1, col2 = st.columns(2)
        with col1:
            codc = st.text_input("Course Code (CodC)", placeholder="e.g., CT123").strip()
            name = st.text_input("Course Name").strip()
        with col2:
            ctype = st.text_input("Course Type (CType)").strip()
            level = st.number_input("Level", min_value=1, max_value=4, step=1)
            
        submitted = st.form_submit_button("Insert Course")
        
        if submitted:
            if not codc or not name or not ctype:
                st.error("All fields are mandatory. Please fill them out.")
            elif not codc.startswith("CT"):
                st.error("Invalid Course Code. It must start with 'CT'.")
            else:
                query = "INSERT INTO COURSES (CodC, Name, CType, Level) VALUES (%s, %s, %s, %s)"
                success = run_query(query, (codc, name, ctype, level), fetch=False)
                if success:
                    st.success(f"Course '{name}' (Code: {codc}) successfully inserted!")

# --- PAGE 5: ADD LESSON ---
elif selection == "Add Lesson":
    st.title("Schedule New Lesson")
    st.markdown("Use this form to add a new lesson to the program. Lessons cannot exceed 60 minutes and must occur between Monday and Friday.")
    
    # Fetch options for dropdowns
    instructors = run_query("SELECT FisCode, Name, Surname FROM INSTRUCTOR")
    courses = run_query("SELECT CodC, Name FROM COURSES")
    
    if instructors and courses:
        inst_dict = {f"{r['FisCode']} - {r['Name']} {r['Surname']}": r['FisCode'] for r in instructors}
        course_dict = {f"{r['CodC']} - {r['Name']}": r['CodC'] for r in courses}
        
        with st.form("add_lesson_form"):
            col1, col2 = st.columns(2)
            
            with col1:
                selected_inst = st.selectbox("Select Instructor:", options=list(inst_dict.keys()))
                selected_course = st.selectbox("Select Course:", options=list(course_dict.keys()))
                day = st.selectbox("Day of Week:", ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"])
                
            with col2:
                # Assuming StartTime is time format (HH:MM)
                start_time = st.time_input("Start Time:", value=datetime.time(9, 0))
                duration = st.slider("Duration (minutes):", min_value=15, max_value=120, value=60, step=15)
                room = st.text_input("Room (e.g., Room A)").strip()
                
            submitted = st.form_submit_button("Schedule Lesson")
            
            if submitted:
                fiscode = inst_dict[selected_inst]
                codc = course_dict[selected_course]
                
                if duration > 60:
                    st.error("Duration limit exceeded. A lesson cannot last more than 60 minutes.")
                elif not room:
                    st.error("Room field cannot be empty.")
                else:
                    # Check for overlaps: No other lessons for the SAME course on the SAME day
                    check_query = "SELECT * FROM PROGRAM WHERE CodC = %s AND Day = %s"
                    overlap = run_query(check_query, (codc, day))
                    
                    if overlap:
                        st.error("Scheduling Conflict: A lesson for this course is already scheduled on this day.")
                        st.write("Current schedule for this day:", pd.DataFrame(overlap))
                    else:
                        insert_query = """
                            INSERT INTO PROGRAM (FisCode, Day, StartTime, Duration, CodC, Room) 
                            VALUES (%s, %s, %s, %s, %s, %s)
                        """
                        params = (fiscode, day, start_time.strftime('%H:%M:%S'), duration, codc, room)
                        success = run_query(insert_query, params, fetch=False)
                        
                        if success:
                            st.success("Lesson scheduled successfully!")
    else:
        st.error("Ensure that both the INSTRUCTOR and COURSES tables have data before scheduling a lesson.")
