import os
import datetime as dt
import camille

start_date = dt.datetime(2018, 1,1)
end_date = dt.datetime.now()

installation = 'HS2'
data_root = '...'

prefix =
    f'{data_root}/processed/lidar/{installation}/lidar-hwindspeed'

windiris_root =
    f'{data_root}/LiDAR_WindIris/Data/{installation}/real_time_data'

bazefetch_root =
    f'{data_root}/bazefield_sensor_extraction/baze_taglist_all_gz'

windiris = camille.source.windiris(windiris_root)
bazefield = camille.source.bazefetcher(bazefetch_root)
pitch_tag = f'HYS-{installation}-MRUNacelle-PitchAngle'
roll_tag = f'HYS-{installation}-MRUNacelle-rollAngle'

date = start_date


def trunc_date(date): return dt.datetime(date.year, date.month, date.day)


def main():
    while date < end_date:
        next_date = trunc_date(date + timedelta(days=1))
        if trunc_date(end_date) == next_date:
            next_date = end_date

        li = windiris(start=date, end=next_date)
        pitch = bazefield(pitch_tag, start=date, end=next_date)
        roll = bazefield(roll_tag, start=date, end=next_date)

        li.rename(columns={
            'Timestamp': 'time',
            'LOS index': 'los_id',
            'RWS': 'radial_windspeed',
            'RWS Status': 'status',
            'Distance': 'distance'},
            inplace=True)

        li = li[['time','los_id','radial_windspeed','status','distance']]
        li['pitch'] = camille.util.resample(pitch, onto=li.time, interp='linear')
        li['roll'] = camille.util.resample(roll, onto=li.time, interp='linear')

        processed = camille.processors.lidar(li)

        datestr = (
            f'_{date.year}{date.month}{date.day}'
            f'_{next_date.year}{next_date.month}{next_date.day}')
        processed.to_csv(prefix + datestr)

        date = next_date


if __name__ == '__main__':
    main()
