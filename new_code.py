import streamlit as st
import pandas as pd

st.title("Interactive Exam Scheduler")

uploaded_file = st.file_uploader(
    "Upload Student Subject Data", accept_multiple_files=False, type='xlsx'
)

if uploaded_file is not None:

    df = pd.read_excel(uploaded_file, engine='openpyxl')

    TERM = st.radio(
        "Select Term",
        ["TERM IV", "TERM V", "TERM VI"],
        horizontal=True
    )

    df_subset = df.iloc[:, 4:]

    term_cols = [col for col in df_subset.columns if str(col).startswith(f'{TERM}__')]
    term_df = df_subset[term_cols].copy()
    term_df.columns = [col.replace(f'{TERM}__', '') for col in term_df.columns]

    cols = term_df.columns
    similarity_matrix = pd.DataFrame(index=cols, columns=cols, dtype=int)
    for col1 in cols:
        for col2 in cols:
            common = (term_df[col1] == term_df[col2]) & term_df[col1].notna() & term_df[col2].notna()
            similarity_matrix.loc[col1, col2] = int(common.sum())


    df = similarity_matrix.copy()
    st.dataframe(df)
    df = df.apply(pd.to_numeric, errors='coerce').fillna(0).astype(int)

    all_subjects = df.index.tolist()
    conflict_graph = {subject: set() for subject in all_subjects}

    num_subjects = len(all_subjects)
    for i in range(num_subjects):
        for j in range(i + 1, num_subjects): # Start from i+1 to avoid duplicate pairs and self-conflicts
            subject1 = all_subjects[i]
            subject2 = all_subjects[j]
            if df.loc[subject1, subject2] > 0:
                conflict_graph[subject1].add(subject2)
                conflict_graph[subject2].add(subject1) # Conflicts are bidirectional

    if 'num_days' not in st.session_state:
        st.session_state.num_days = 5 # Default number of days

    if 'schedule' not in st.session_state:
        st.session_state.schedule = {
            day: {slot: [] for slot in range(1, 4)} for day in range(1, st.session_state.num_days + 1)
        }

    def on_multiselect_change(day, slot_num):
        new_subjects_list = st.session_state[f"day_{day}_slot_{slot_num}_multiselect"]

        new_subjects_list = list(set(new_subjects_list))

        for i in range(len(new_subjects_list)):
            for j in range(i + 1, len(new_subjects_list)):
                s1 = new_subjects_list[i]
                s2 = new_subjects_list[j]
                if s1 in conflict_graph.get(s2, set()) or s2 in conflict_graph.get(s1, set()):
                    st.session_state.schedule[day][slot_num] = st.session_state.get(f"last_valid_day_{day}_slot_{slot_num}", [])
                    return # Stop further validation and update

        if len(new_subjects_list) > 5:
            st.session_state.schedule[day][slot_num] = st.session_state.get(f"last_valid_day_{day}_slot_{slot_num}", [])
            return

        # 3. Validate that subjects are not scheduled elsewhere already
        # Get all subjects currently scheduled across ALL slots (excluding the current slot's new selection temporarily)
        all_currently_scheduled_except_this_slot = set()
        for check_day, slots_on_check_day in st.session_state.schedule.items():
            for check_slot_num, subjects_in_check_slot in slots_on_check_day.items():
                if check_day == day and check_slot_num == slot_num:
                    continue # Skip the current slot's existing subjects for this check

                all_currently_scheduled_except_this_slot.update(subjects_in_check_slot)

        for s in new_subjects_list:
            if s in all_currently_scheduled_except_this_slot:
                st.session_state.schedule[day][slot_num] = st.session_state.get(f"last_valid_day_{day}_slot_{slot_num}", [])
                return

        # If all validations pass, update the schedule in session state with the new list
        st.session_state.schedule[day][slot_num] = new_subjects_list
        # Store the valid state for potential reversion
        st.session_state[f"last_valid_day_{day}_slot_{slot_num}"] = new_subjects_list

    def update_num_days_callback():
        """Callback for when the number of days slider changes."""
        # Only update if the value has actually changed
        if st.session_state.num_days_input != st.session_state.num_days:
            st.session_state.num_days = st.session_state.num_days_input
            # Reset the entire schedule when the number of days changes
            reset_schedule()
            st.rerun()

    def reset_schedule():
        st.session_state.schedule = {
            day: {slot: [] for slot in range(1, 4)} for day in range(1, st.session_state.num_days + 1)
        }
        # Clear last valid states as well
        for day in range(1, st.session_state.num_days + 1):
            for slot in range(1, 4):
                if f"last_valid_day_{day}_slot_{slot}" in st.session_state:
                    del st.session_state[f"last_valid_day_{day}_slot_{slot}"]


    # --- Streamlit UI Layout ---
    st.title("Interactive Exam Scheduler")
    # Sidebar for controls (e.g., Reset button, Number of Days)
    st.sidebar.header("Controls")

    # Number of days input
    st.sidebar.number_input(
        "Number of Days",
        min_value=1,
        max_value=10, # Set a reasonable max value
        value=st.session_state.num_days,
        key="num_days_input",
        on_change=update_num_days_callback,
        help="Select the total number of days for the exam schedule."
    )

    if st.sidebar.button("Reset Schedule", help="Clear all scheduled subjects and start over."):
        reset_schedule()
        st.rerun() # Rerun the app to immediately reflect the cleared schedule

    num_days = st.session_state.num_days # Use the dynamic number of days
    num_slots_per_day = 3 # Fixed as per requirement

    header_cols = st.columns([1] + [3] * num_slots_per_day)
    header_cols[0].write("**Day / Slot**")
    for i in range(num_slots_per_day):
        header_cols[i+1].write(f"**Slot {i+1}**")

    all_currently_scheduled_subjects = set()
    for d_key in range(1, num_days + 1):
        if d_key in st.session_state.schedule: # Ensure the day exists in the schedule
            for s_key, subjects_list in st.session_state.schedule[d_key].items():
                all_currently_scheduled_subjects.update(subjects_list)

    for day in range(1, num_days + 1):
        cols = st.columns([1] + [3] * num_slots_per_day)
        cols[0].write(f"**Day {day}**")

        for slot_num in range(1, num_slots_per_day + 1):
            if day not in st.session_state.schedule or slot_num not in st.session_state.schedule[day]:
                st.session_state.schedule[day] = st.session_state.schedule.get(day, {})
                st.session_state.schedule[day][slot_num] = []

            current_subjects_in_slot = st.session_state.schedule[day][slot_num]

            st.session_state[f"last_valid_day_{day}_slot_{slot_num}"] = current_subjects_in_slot

            conflicting_with_current_slot_selection = set()
            for selected_sub_in_current_slot in current_subjects_in_slot:
                conflicting_with_current_slot_selection.update(conflict_graph.get(selected_sub_in_current_slot, set()))

            final_options_for_multiselect = []
            for sub in all_subjects:
                if sub in current_subjects_in_slot:
                    final_options_for_multiselect.append(sub)
                elif (sub not in all_currently_scheduled_subjects and
                    sub not in conflicting_with_current_slot_selection):
                    final_options_for_multiselect.append(sub)

            final_options_for_multiselect.sort() # Keep options sorted for consistent display

            cols[slot_num].multiselect(
                label=f"Select subjects for Day {day} Slot {slot_num}",
                options=final_options_for_multiselect, # Use the dynamically filtered options
                default=current_subjects_in_slot, # Show current selections from session state
                key=f"day_{day}_slot_{slot_num}_multiselect", # Unique key for the widget
                placeholder="Choose subjects...",
                on_change=on_multiselect_change, # Assign the callback function
                args=(day, slot_num,) # Pass arguments to the callback
            )
