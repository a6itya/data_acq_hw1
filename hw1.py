import json
import re

import pandas as pd
import streamlit as st

from google.cloud import storage

from user_definition import GCP_BUCKET_NAME, GCP_FILE_NAME


def retrieve_data_from_gcs(bucket_name: str,
                           file_name: str
                           ) -> dict:
    """
    TODO: Retrieve file, called `file_name` from `bucket_name`
        and returns a dictionary including "results",
        "job_title", and "company_dict"

        Args:
            bucket_name (str) : bucket name
            file_name (str) : file_name to retrieve data.

        Returns:
            retrieves file in dictionary format

    Hint :
    The `file_name` is a public file, which does not require
    authentification and you can create an anonymous client via
    storage.Client.create_anonymous_client()
    """
    # anonymous client, since the file is public
    client = storage.Client.create_anonymous_client()
    # finds bucket (bucket_name)
    bucket = client.bucket(bucket_name)
    # finds file (blob(file_name))
    blob = bucket.blob(file_name)
    # downloads blob
    contents = blob.download_as_text()
    # converts from string to dict
    return json.loads(contents)


def summarize_distribution(df: pd.DataFrame, column_name: str, 
                           top_n: int = 10) -> dict:
    """
    TODO:
    df[column_name] has a list per row (e.g. skills per job).
    Explode using pandas .explode() from a list into individual items
    first, then count how many rows each item appears in across the
    whole column.
    Return the top_n most frequent items.
    Ex. [['a','b','c'], ['a','d']], top_n=2 -> {'a': 2, 'b': 1}
    """
    skills = df[column_name].explode()
    counts = skills.value_counts()
    return counts.head(top_n).to_dict()


if __name__ == '__main__':
    results = retrieve_data_from_gcs(GCP_BUCKET_NAME, GCP_FILE_NAME)

    """
    TODO:
    1. Add title (`'job_title'` Listings and Skills) for the chosen
    `'job_title` from the retrieved data.
    2. Build a **sorted** list of company display names (the dict's
    keys) to display on the sidebar.
    3. For each company, render an `st.checkbox` (default `value=True`)
    with the company name as its label on the side bar.
    4. Filter data down to only the rows whose `"link"` column contains
    **any** of the substrings in the selected company in the step 2.
    Note: To check the substring, ensure it is case insenstive
    (Ex. "Anthropic" ->
    "https://job-boards.greenhouse.io/anthropic/jobs/5297059008")
    If no companies are selected, the filtered result should be empty —
    not "everything." (Hint: `str.contains()` accepts a regex; joining
    your substrings with `"|"` builds an OR pattern.) Note: If you are
    not familiar with regex but want to try for this question, feel free
    to get GenAI's help. But ensure to attribute/cite the model you used
    and what you requested (ex. Anthropic opus-5, create regex pattern
    to filter strings containing any values in a list) as a comment
    5. Keep only the `"date"`, `"title"`, `"skills"` and `"link"`
    columns.
    6. Drop duplicate rows by `"link"`.
    7. Sort by `"date"` descending, so the newest postings show first.
    Optional : Sort by `"title"` for the same `"date"`.
    8. Display the result with `st.dataframe(...)`, using
    `st.column_config.LinkColumn()` on the `"link"` column so it renders
    as a clickable link rather than raw text.
    9. Display the `summarize_distribution(df)` using `st.bar_chart(...)`
    as a bar chart.
    """
    company_dictionary = results["company_dict"]
    job_title = results["job_title"]
    data = pd.DataFrame(results["results"])

    # 1. title for the chosen job_title
    st.title(f"{job_title} Listings and Skills")

    # 2. sorted company display names
    company_names = sorted(company_dictionary.keys())
    selected_companies = []

    # 3. one checkbox per company, on by default
    with st.sidebar:
        st.write("Filter by Company")
        for company in company_names:
            if st.checkbox(company, value=True):
                selected_companies.append(company)

    # 4. keep rows whose link contains any selected company name.
    # Regex pattern written with help from Anthropic Claude Opus 5:
    # asked for a regex matching strings containing any value in a
    # list, case-insensitively.
    if selected_companies:
        pattern = "|".join(re.escape(name) for name in selected_companies)
        mask = data["link"].str.contains(pattern, case=False, na=False)
        filtered_df = data.loc[mask].copy()
    else:
        # nothing selected -> empty table, not every row
        filtered_df = data.iloc[0:0].copy()

    # 5. keep only the four required columns
    filtered_df = filtered_df[["date", "title", "skills", "link"]]
    # 6. drop duplicate links
    filtered_df = filtered_df.drop_duplicates(subset="link")
    # 7. newest first, then title ascending within the same date
    filtered_df = filtered_df.sort_values(by=["date", "title"],
                                          ascending=[False, True])

    # 8. render the table with a clickable link column
    st.dataframe(filtered_df,
                 hide_index=True,
                 column_config={
                     "link": st.column_config.LinkColumn()})

    # 9. bar chart of the most mentioned skills (default top_n)
    skill_counts = summarize_distribution(filtered_df, "skills")
    skill_chart = pd.DataFrame({"Skill": list(skill_counts.keys()),
                                "Count": list(skill_counts.values())})
    skill_chart = skill_chart.set_index("Skill")

    st.bar_chart(skill_chart)
