drop table if exists users;
create table users (
  id integer primary key autoincrement,
  username string not null,
  password string not null,
  first_name string not null,
  last_name string not null,
  authorized integer,
  identifier string,
  shard_id string,
  isadmin integer,
  leadID integer
);

insert into users (username, password, first_name, last_name, isadmin) values ('Admin', 'Admin', 'Admin', 'Admin', 1);
