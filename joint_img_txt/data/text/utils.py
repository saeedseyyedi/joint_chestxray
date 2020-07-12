import pandas as pd
from ast import literal_eval
import csv
import re
import numpy as np
import random
from tqdm import tqdm_notebook as tqdm

'''
Related to the original class files shared by Ray
'''
# reads individual class{num}.txt files to return the data as a list
# is a helper function for train_filename_df function
def read_class_file(res, classfile_name, prediction_label):
    data = []
    with open(res(classfile_name)) as file:
        for line in file.readlines():
            filename, keywords = line.split(':')
            keywords = keywords.strip().split(';')
            if keywords[-1] == '': keywords = keywords[:-1]
            metadata = {'keywords_found': keywords}
            data.append([filename.strip(), int(prediction_label), metadata])
    return data

# returns all the train data filenames, read from the class*.txt files
# need to remove the test filenames from here before writing the csv 
def train_filename_df(res):
    data = read_class_file(res, 'class0.txt', 0)
    data.extend(read_class_file(res, 'class1.txt', 1))
    data.extend(read_class_file(res, 'class2.txt', 2))
    data.extend(read_class_file(res, 'class3.txt', 3))
    df = pd.DataFrame(data, columns='filename,edema_severity,metadata'.split(','))
    return df

# returns the test filename: reads the csv file that was generated by radiologist label
# note that these rows need to be removed from the train_filename.csv 
def test_filename_df(res, edema_pred_dict):
    data = []
    with open(res('report_label.csv')) as csv_file:
        csv_reader = csv.reader(csv_file, delimiter=',')
        line_count = 0
        for row in csv_reader:
            if line_count == 0:
                line_count +=1  # because the first row contains column names
                continue
            if row[1].lower() == '':
                print('Radiologist (Seth) did not label report: s'+row[0])
                continue
            edema_label = edema_pred_dict[row[1].lower()]
            keywords_found = row[5].strip().split(';')
            if keywords_found[-1] == '': keywords_found = keywords_found[:-1]
            keyword_searching_edema_label = edema_pred_dict[row[4].lower()] # this is the prediction label from automatic keyword search
            metadata = {'keywords_found': keywords_found, 
                        'keyword_search_edema_severity': keyword_searching_edema_label}
    #         row[4] is the keyword search prediction
    #         row[5] is the keywords detected
            data.append(['s'+ row[0], edema_label, metadata])
        df = pd.DataFrame(data, columns='filename,edema_severity,metadata'.split(','))
        duplicated_rows = df.groupby(['filename']).count()
        duplicated_rows = duplicated_rows.loc[duplicated_rows['edema_severity'] > 1]
        print("Original test data frame is %d long but there are %d duplicated rows"%(
            len(df), len(duplicated_rows)))
        df = df.drop_duplicates(subset="filename").reset_index(drop="True") # seems like the test data has 21 duplicated
        # filenames so need to remove those to return 178 files
        print("Removed duplicates to return %d length dataframe"%(len(df)))
        return df, duplicated_rows.index.values.tolist()

'''
Do the reading and the writing of the dataframe - more general purpose code
'''
# to streamline the writing of the dataframe
def write_dataframe(df, filepath):
    df.to_csv(filepath, sep='\t', encoding='utf-8', index=False)

# to streamline the reading of the dataframe
def read_dataframe(filepath):
    df = pd.read_csv(filepath, sep='\t')
    def literal_eval_col(row, col_name):
        col = row[col_name]
        col = literal_eval(col)
        return col
    df['metadata'] = df.apply(literal_eval_col, args=('metadata',), axis=1)
    if 'normalized_report' in df.columns:
        df['normalized_report'] = df.apply(literal_eval_col, args=('normalized_report',), axis=1)
    #df['edema_severity'] = df.apply(literal_eval_col, args=('edema_severity',), axis=1)
    # metadata is a dictionary which is written into the csv format as a string
    # but in order to be treated as a dictionary it needs to be evaluated
    return df

# The goal here is to make sure that the df that is written into memory is the same one that is read
def check_equality_of_written_and_read_df(df, df_copy):
    bool_equality = df.equals(df_copy)
    # to double check, we want to check with every column
    bool_every_column = True
    for idx in range(len(df)):
        row1 = df.iloc[idx]
        row2 = df_copy.iloc[idx]
        # for any column names (grab the column names), then compare for all of them and print the 
        # column name where they differ
        if not np.array_equal(row1.index, row2.index):
            print("The two dataframes must have identical columns with their order!")
            return
        columns = row1.index
        for column_name in columns:
            if row1[column_name] != row2[column_name]:
                print("The dataframes differ in column: ", column_name)
                bool_every_column = False
                return bool_equality, bool_every_column
    return bool_equality, bool_every_column


# Gathers data from the findings and impressions sections of the report
# Usage: utils.write_report_into_df(df_filename,
# res='/crimea/geeticka/data/chestxray/pre-processed/lm_reports/original_reports.csv'
def write_report_into_df(df_filename, original_reports_df, semisupervised=False):
    length = 0
    empty_reports = 0 # counts how many reports don't have findings, impression, conclusion and
    # recommendation sections
    reports = []
    origin_sections = [] # Information about the section of the reports where the text comes from
    filenames = df_filename['filename'].unique().tolist()
    # there are cases when there are no findings. In that case you should extract impressions. 
    for filename in tqdm(filenames):
        report = ''
        origin_sec = []
        row = original_reports_df[original_reports_df['filename'] == filename]
        report_dict = row['report'].values[0]
        sections_to_find = ['finding', 'impression', 'conclusion', 'recommendation']
        values_found = [] # a list of all values found within the dictionary; possibly a list of lists
        # check for fully empty reports - some reports have empty final_report sections
        if isinstance(report_dict['final_report'], str):
            report = report_dict['final_report']
            report = remove_whitespace(report)
            if not report:
                print('report %s is empty'%filename)
            reports.append(report)
            origin_sections.append(origin_sec)
            continue

        for section in sections_to_find:
            keys_found = []
            sections_found = []
            final_report = report_dict['final_report']
            for s in final_report.keys():
                if section in s:
                    keys_found.append(s)
                    sections_found.append(section)
            if len(keys_found) > 0:
                values_needed = [final_report[key] for key in keys_found]
                # only add the values for the non duplicated keys
                for val in values_needed:
                    if val not in values_found:
                        values_found.append(val)
                for sec in sections_found:
                    if sec not in origin_sec:
                        origin_sec.append(sec)
        for val in values_found:
            if type(val) is list:
                report += ' '.join(val) + ' '
            else:
                report += val + ' '
                
        #if any('finding' in s for s in report_dict['final_report'].keys()) and report_dict['final_report']['findings']:
        #    origin_sec.append('findings')
        #    report += report_dict['final_report']['findings'] + ' ' 
        #if 'impression' in report_dict['final_report'].keys() and report_dict['final_report']['impression']:
        #    origin_sec.append('impression')
        #    report += ' ' + report_dict['final_report']['impression']
        report = remove_whitespace(report)
        # In case no sections we looked for were found and we are in the semisupervised case, 
        # just append the final report values in their entirety and treat that as the report
        if semisupervised == True and not report:
            empty_reports += 1
            final_report = report_dict['final_report']
            if isinstance(final_report, str):
                final_report = remove_whitespace(final_report)
            edema_severity = df_filename[df_filename['filename'] == filename]['edema_severity'].values[0]
            if edema_severity == -1 and final_report: # we only want to do this for the unlabeled report
                final_report_as_list = [] # sometimes we have final report values as strings, other times we 
                # have them as lists, and need to get it all as one list rather than list of lists
                for val in final_report.values():
                    if isinstance(val, str):
                        final_report_as_list.append(val)
                    elif isinstance(val, list):
                        final_report_as_list.append(' '.join(val))
                    else:
                        print('Report %s has values in final_report that are not string or list'%filename)
                report += ' '.join(final_report_as_list)
                origin_sec = ['final_report']
            else:
                print('report %s is empty'%filename)
        reports.append(report)
        origin_sections.append(origin_sec)
    df_new = df_filename.copy()
    df_new.insert(2, "original_report", reports)
    df_new['origin_section'] = origin_sections
    def add_to_metadata(row):
        metadata = row.metadata
        origin_section = row.origin_section
        metadata['origin_section'] = origin_section
        return metadata
    df_new['metadata'] = df_new.apply(add_to_metadata, axis=1)
    df_new.drop('origin_section', axis=1, inplace=True)
    if semisupervised == True:
        return df_new, empty_reports
    return df_new

## Gathers data from the findings section as a report. If findings are not present in the report
## gather information from impressions.
## Usage: utils.write_report_into_df(df_filename, res='/data/medg/misc/geeticka/old_chestxray')
## i.e. you will use the directory where the original reports have been written
#def write_report_into_df(df_filename, res):
#    length = 0
#    reports = []
#    origin_sections = [] # Information about the section of the reports where the text comes from
#    filenames = df_filename['filename'].unique().tolist()
#    # there are cases when there are no findings. In that case you should extract impressions. 
#    for filename in filenames:
#        file = res('reports/' + filename)
#        with open(file, 'r') as text_file:
#            length += 1
#            startprinting = False
#            findings = ''
#            for line in text_file.readlines():
#                # below is assuming that only findings are located in the report
#                # in the cases when finding is not present, use impressions/conclusion. s
#                line = line.strip()
#                if line.startswith('FINDING'):
#                    startprinting = True
#                if startprinting == True and not line.startswith('IMPRESSION') \
#                and not line.startswith('CONCLUSION'):
#                    line = line.replace('_', '') 
#                    # remove the instances of __ which are de-identification symbols
#                    if line.startswith('FINDINGS:'):
#                        m = re.search('(?<=^FINDINGS:).*', line)
#                        line = m.group(0).strip()
#                        if line != '':
#                            findings += ' ' + line
#                    else:
#                        findings += ' ' + line
#                if line.startswith('IMPRESSION') or line.strip().startswith('CONCLUSION'):
#                    break # we are not using impression and conclusion at the moment.
#            if findings.strip() != '':
#                reports.append(findings)
#                origin_sections.append('findings')
#                continue # continue if findings exist
##         print(file)
#        with open(file, 'r') as text_file:
#            startprinting = False
#            impressions = ''
#            for line in text_file.readlines():
#                line = line.strip()
#                if line.startswith('IMPRESSION'):
#                    startprinting = True
#                if startprinting == True:
#                    line = line.replace('_', '')
#                    if line.startswith('IMPRESSION:'):
#                        m = re.search('(?<=^IMPRESSION:).*', line)
#                        line = m.group(0).strip()
#                        if line != '':
#                            impressions += ' ' + line
#                    else:
#                        impressions += ' ' + line
##             if impressions.strip() != '':
#            reports.append(impressions)
#            origin_sections.append('impression')
#    df_new = df_filename.copy()
#    df_new.insert(2, "original_report", reports)
#    df_new['origin_section'] = origin_sections
#    def add_to_metadata(row):
#        metadata = row.metadata
#        origin_section = row.origin_section
#        metadata['origin_section'] = origin_section
#        return metadata
#    df_new['metadata'] = df_new.apply(add_to_metadata, axis=1)
#    df_new.drop('origin_section', axis=1, inplace=True)
#    return df_new

# The following method is related to generating train and dev csv files for the BERT processing
# given the train and test data, return a new train and dev set with similar individual class ratios as 
# train vs test data
def get_new_train_dev_df(train_df, test_df):
    if not np.array_equal(train_df.columns, test_df.columns):
        print("Please make sure to match columns in the two dataframes passed")
        return
    new_train_data = []
    new_dev_data = []
    edema_severities = train_df['edema_severity'].unique()
    for severity in edema_severities:
        train_length = len(train_df.loc[train_df['edema_severity'] == severity])
        test_length = len(test_df.loc[test_df['edema_severity'] == severity])
        ratio = test_length/train_length
        new_train_length = round(train_length/(1+ratio))
        new_dev_length = train_length - new_train_length
        print('Suggested length for the new train, dev set for label %d is: %d for train and %d for dev'%(
        severity, new_train_length, new_dev_length))

        train_indexes = train_df.loc[train_df['edema_severity'] == severity].index.tolist()
        new_dev_indexes = random.sample(train_indexes, new_dev_length)
        new_train_indexes = list(set(train_indexes) - set(new_dev_indexes))
        for index in new_dev_indexes:
            new_dev_data.append(train_df.iloc[index].values) # adding a tolist() might be necessary
        for index in new_train_indexes:
            new_train_data.append(train_df.iloc[index].values)

    new_train_df = pd.DataFrame(new_train_data, columns=train_df.columns)
    new_dev_df = pd.DataFrame(new_dev_data, columns=train_df.columns)
    return new_train_df, new_dev_df

# get a dictionary, return a string
def extract_report_from_normalized(normalized_report):
    return " ".join(normalized_report['sentences'])

'''
Below are helper functions for generating the tsv files
'''
# remove any additional whitespace within a line
def remove_whitespace(line):
    return str(" ".join(line.split()).strip())

# Convert edema severity to ordinal encoding
def convert_to_ordinal(severity):
    if severity == 0:
        return '000'
    elif severity == 1:
        return '100'
    elif severity == 2:
        return '110'
    elif severity == 3:
        return '111'
    elif severity == -1: # handling the semi supervised case
        return '-1'
    else:
        raise Exception("Severity can only be between 0 and 3 or can be -1")

# Convert to the df bert expects for the multilabel case
def get_df_bert(df, output_channel_encoding='multilabel'):
    data = []
    i = 0
    def get_num_from_filename(filename):
        filenum = filename.split('.')
        filenum = filenum[0][1:]
        return filenum

    if output_channel_encoding == 'multilabel':
        label_converter = convert_to_ordinal
    elif output_channel_encoding == 'multiclass':
        label_converter = str # passing it the string function to convert an integer to string
    for index, row in df.iterrows():
        report = extract_report_from_normalized(row['normalized_report'])
        label = label_converter(row['edema_severity'])
        report_id = get_num_from_filename(row['filename'])
        data.append([i, label, report_id, 'a', report])
        i += 1
    df_bert = pd.DataFrame(data, columns='id,label,report_id,alpha,text'.split(','))
    return df_bert
