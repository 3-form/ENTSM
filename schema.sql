drop table if exists users;
create table users (
  id integer primary key autoincrement,
  username string not null,
  password string not null,
  first_name string not null,
  last_name string not null,
  email_address string not null,
  use_email string,
  authorized integer,
  identifier string,
  shard_id string,
  notebook_ids string,
  isadmin integer,
  leadID integer
);

insert into users (username, password, first_name, last_name, email_address, isadmin) values ('Admin', 'Admin', 'Admin', 'Admin', 'Admin', 1);
