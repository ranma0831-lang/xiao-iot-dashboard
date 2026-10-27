-- Supabase 대시보드 > SQL Editor 에서 한 번 실행
create table if not exists devices (
  id text primary key,
  led boolean not null default false
);

create table if not exists sensor_readings (
  id bigint generated always as identity primary key,
  device_id text not null references devices(id),
  temperature real not null,
  rssi int not null,
  created_at timestamptz not null default now()
);
create index if not exists sensor_readings_device_time on sensor_readings (device_id, created_at desc);

-- 백엔드는 service_role 키로 접근(RLS 우회). 정책 없이 RLS만 켜서 anon 키로는 접근 불가하게 함
alter table devices enable row level security;
alter table sensor_readings enable row level security;

insert into devices (id) values ('xiao-01') on conflict do nothing;
