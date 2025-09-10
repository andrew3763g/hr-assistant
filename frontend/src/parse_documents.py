import os
from glob import glob
def convert_file_to_text(in_file, out_file):
    ''' Function calls java -jar tike with in_file and out_file parameters
    apache tika parses any document to txt format
    '''
    print(f'java -jar tika-app-3.2.2.jar -t \'{in_file}\' > \'{out_file}\'')
    os.system(f'java -jar tika-app-3.2.2.jar -t \'{in_file}\' > \'{out_file}\'')

def convert_dir(dir_raw, dir_new):
    '''convert all files from dir_raw to txt files in dir_new'''
    for i in glob(f'{dir_raw}/*'):
        print(F'Converting file {i}...')
        i2 = i.replace(dir_raw,dir_new)
        i2 = i2.split('.')[:-1][0]+'.txt'
        convert_file_to_text(i,i2)
        print(i2)

def conver_resume_vacancies():
    '''convert resumes and vacancies to txt format'''
    convert_dir('resume_raw','resume')
    convert_dir('vacancy_raw', 'vacancy')

if __name__ == '__main__':
    conver_resume_vacancies()
