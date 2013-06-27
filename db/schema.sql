drop table if exists users;
create table users (
  id integer primary key autoincrement,
  username string not null,
  password string not null,
  first_name string not null,
  last_name string not null,
  email_address string not null,
  use_email integer,
  authorized integer,
  auth_token string,
  shard_id string,
  notebook_ids string,
  is_admin integer,
  lead_id sring
);

insert into users (username, password, first_name, last_name, email_address, is_admin) values ('Admin', 'Admin', 'Admin', 'Admin', 'Admin', 1);
