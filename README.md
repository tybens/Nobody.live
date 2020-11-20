# lonelyraids.com

A websocket (flask-socketio) modification to jkingsman's [Nobody.live](https://github.com/jkingsman/Nobody.live) to allow users to perform "raids" (in this case, where users all collectively tune in to the same stream stream) on twitch streamers with zero viewers.

## TODO:
- [x] add websocket to broadcast when a raid is started to all clients 
- [x] add client counter, to show users how many people are joining them on a raid
- [x] add a message to invite friends! what's a raid without your friends...
- [ ] group functionality - users can make individual groups to invite their friends and perform a raid with more individual control (rather than server-wide raids)
- [ ] button to override current raid, if majority of current clients hit the button 
- [ ] ABOUT drop down to describe what a raid is and how the button works
- [ ] ~change main button style~

## architecture

A worker script (`scanner.py`) loops through the Twitch API's list of streams and spins until it inserts all streamers it finds matching the search criteria (default zero viewers), then it starts again. These streamers are inserted as expiring keys on the assumption that someone will view them and then they won't have zero viewers any more so should not be served for too long. If a stream still has zero viewers on a subsequent pass, the insertion into Redis will override the old expiration time and they'll stick around for a while longer.

Environment variables to be set:

* `CLIENT_ID`: Your Twitch application client ID (found at https://dev.twitch.tv/console)
* `CLIENT_SECRET`: Your Twitch application client secret (found at https://dev.twitch.tv/console)

Meanwhile, the Flask app in `app.py` serves the index and the endpoint to get a random streamer.

## getting up and running

* Install dependencies to unique environment `pip install -r requirements.txt`
* Install and start Redis
* Run the stream fetcher (e.g. `CLIENT_ID=xxxxxx CLIENT_SECRET=xxxxxx scanner.py`). This will need to run continuously.
* Run the flask app (`flask run`)

This is obviously not production ready; you'll need to make sure all services are running as daemons (some config files are included in `etc`) and that your flask app is running safely (e.g. behind gunicorn/nginx/pick your poison) (SEE `setting up deployment`)

## fully deploying (`setup.txt`)

This is the process for full deployment, this is not the setup for a local server. See above for directions for setting up a local server

```bash
cd /srv # wherever we want the app to be
git clone https://github.com/tybens/lonelyraids.com.git
cd lonelyraids.com
sudo apt-get update
sudo apt install python3-pip python3-dev python3-venv nginx
python3 -m venv venv
source venv/bin/activate
sudo pip3 install -r requirements.txt

# static files
sudo mkdir /var/www/static
sudo mv -v static/* /var/www/static/
sudo chown 755 /var/www/static

# nginx config
sudo mv etc/lr-nginx /etc/nginx/sites-available/lr-nginx
sudo ln -s /etc/nginx/sites-available/lr-nginx /etc/nginx/sites-enabled/
sudo systemctl restart nginx
sudo ufw allow 'Nginx Full'  # not sure if this is necessary (the article said it was)

# redis setup
sudo wget http://download.redis.io/redis-stable.tar.gz
tar xvzf redis-stable.tar.gz
cd redis-stable
sudo make install

# supervisor setup
mkdir /var/log/streams
sudo mv etc/supervisor_services.conf /etc/supervisord.conf
sudo supervisord -c /etc/supervisord.conf  # starts supervisord services

# certbot setup (for https:// ssl verification)
sudo snap install core
sudo snap refresh core
sudo snap install --classic certbot
sudo ln -s /snap/bin/certbot /usr/bin/certbot
sudo certbot --nginx

deactivate # deactivate venv...
```


## dependencies

Update direct dependencies in `requirements.in`; use `pip-compile` to compile them down to `requirements.txt` if you update them.
