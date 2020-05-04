# ----------------------------------------------------------------------------#
# Imports
# ----------------------------------------------------------------------------#

import dateutil.parser
import babel
from flask import Flask, render_template, request, flash, redirect, url_for
from flask_moment import Moment
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
import logging
from logging import Formatter, FileHandler
from forms import *

# ----------------------------------------------------------------------------#
# App Config.
# ----------------------------------------------------------------------------#

app = Flask(__name__)
moment = Moment(app)
app.config.from_object('config')
db = SQLAlchemy(app)
migrate = Migrate(app, db)

# ----------------------------------------------------------------------------#
# Models.
# ----------------------------------------------------------------------------#


class Venue(db.Model):
    __tablename__ = 'venues'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String, nullable=False)
    city = db.Column(db.String(120), nullable=False)
    state = db.Column(db.String(120), nullable=False)
    address = db.Column(db.String(120), nullable=False)
    phone = db.Column(db.String(120), nullable=True)
    genres = db.Column(db.ARRAY(db.String(20)), nullable=False)
    image_link = db.Column(db.String(500), nullable=False)
    facebook_link = db.Column(db.String(120), nullable=True)
    website = db.Column(db.String(120), nullable=True)
    is_seeking_talent = db.Column(db.Boolean, nullable=False, default=True)
    seeking_description = db.Column(db.String(200), nullable=False, default='Looking for talented performers!')
    shows = db.relationship('Show', backref='venue', cascade='all, delete-orphan', lazy=True)


class Artist(db.Model):
    __tablename__ = 'artists'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String, unique=True, nullable=False)
    city = db.Column(db.String(120), nullable=False)
    state = db.Column(db.String(120), nullable=False)
    phone = db.Column(db.String(120), nullable=True)
    genres = db.Column(db.ARRAY(db.String(20)), nullable=False)
    image_link = db.Column(db.String(500), nullable=False)
    facebook_link = db.Column(db.String(120), nullable=True)
    website = db.Column(db.String(120), nullable=True)
    is_seeking_venue = db.Column(db.Boolean, nullable=False, default=True)
    seeking_description = db.Column(db.String(200), nullable=False, default='Looking for venues to perform at!')
    shows = db.relationship('Show', backref='artist', lazy=True)


class Show(db.Model):
    __tablename__ = 'shows'

    id = db.Column(db.Integer, primary_key=True)
    venue_id = db.Column(db.Integer, db.ForeignKey('venues.id'), nullable=False)
    artist_id = db.Column(db.Integer, db.ForeignKey('artists.id'), nullable=False)
    start_time = db.Column(db.DateTime, nullable=False)

# ----------------------------------------------------------------------------#
# Filters.
# ----------------------------------------------------------------------------#


def format_datetime(value, format='medium'):
    date = dateutil.parser.parse(value)
    if format == 'full':
        format = "EEEE MMMM, d, y 'at' h:mma"
    elif format == 'medium':
        format = "EE MM, dd, y h:mma"
    return babel.dates.format_datetime(date, format)


app.jinja_env.filters['datetime'] = format_datetime


# ----------------------------------------------------------------------------#
# Controllers.
# ----------------------------------------------------------------------------#

@app.route('/')
def index():
    return render_template('pages/home.html')


#  Venues
#  ----------------------------------------------------------------

@app.route('/venues')
def venues():
    states = [state[0] for state in db.session.query(Venue.state).order_by(Venue.state).distinct().all()]
    data = []

    for state in states:
        cities = [city[0] for city in
                  db.session.query(Venue.city).filter_by(state=state).order_by(Venue.city).distinct().all()]
        for city in cities:
            venues_query = Venue.query.filter_by(state=state, city=city).order_by(Venue.name).all()
            venues = [{'id': venue.id,
                       'name': venue.name,
                       'num_upcoming_shows': Show.query.filter(Show.venue_id == venue.id,
                                                               Show.start_time > datetime.now()).count()}
                      for venue in venues_query]
            data.append({'city': city,
                         'state': state,
                         'venues': venues})

    return render_template('pages/venues.html', areas=data)


@app.route('/venues/search', methods=['POST'])
def search_venues():

    search_term = request.form.get('search_term', '')
    venues_query = Venue.query.filter(Venue.name.ilike(f'%{search_term}%')).all()

    response = {
        'count': len(venues_query),
        'data': [{'id': venue.id,
                  'name': venue.name,
                  'num_upcoming_shows': Show.query.filter(Show.venue_id == venue.id,
                                                          Show.start_time > datetime.now()).count()}
                 for venue in venues_query]
    }

    return render_template('pages/search_venues.html', results=response,
                           search_term=search_term)


@app.route('/venues/<int:venue_id>')
def show_venue(venue_id):

    try:
        venue = Venue.query.filter_by(id=venue_id).all()[0]
    except:
        return render_template('errors/404.html')

    past_shows = [{
        "artist_id": show.artist.id,
        "artist_name": show.artist.name,
        "artist_image_link": show.artist.image_link,
        "start_time": str(show.start_time)
    } for show in Show.query.filter(Show.venue_id == venue.id, Show.start_time < datetime.now()).all()]

    upcoming_shows = [{
        "artist_id": show.artist.id,
        "artist_name": show.artist.name,
        "artist_image_link": show.artist.image_link,
        "start_time": str(show.start_time)
    } for show in Show.query.filter(Show.venue_id == venue.id, Show.start_time > datetime.now()).all()]

    data = {
        "id": venue.id,
        "name": venue.name,
        "genres": venue.genres,
        "address": venue.address,
        "city": venue.city,
        "state": venue.state,
        "phone": venue.phone,
        "website": venue.website,
        "facebook_link": venue.facebook_link,
        "seeking_talent": venue.is_seeking_talent,
        "seeking_description": venue.seeking_description,
        "image_link": venue.image_link,
        "past_shows": past_shows,
        "upcoming_shows": upcoming_shows,
        "past_shows_count": len(past_shows),
        "upcoming_shows_count": len(upcoming_shows),
    }

    return render_template('pages/show_venue.html', venue=data)


#  Create Venue
#  ----------------------------------------------------------------

@app.route('/venues/create', methods=['GET'])
def create_venue_form():
    form = VenueForm()
    return render_template('forms/new_venue.html', form=form)


@app.route('/venues/create', methods=['POST'])
def create_venue_submission():
    error = False

    try:
        venue = Venue(name=request.form['name'], city=request.form['city'], state=request.form['state'],
                      address=request.form['address'], phone=request.form['phone'],
                      image_link=request.form['image_link'],
                      facebook_link=request.form['facebook_link'],
                      website=request.form['website'], genres=request.form.getlist('genres'))
        db.session.add(venue)
        db.session.commit()
    except:
        error = True
    finally:
        db.session.close()

    if error:
        flash('An error occurred. Venue ' + request.form['name'] + ' could not be listed.')
        return redirect(url_for('create_venue_form'))
    else:
        flash('Venue ' + request.form['name'] + ' was successfully listed!')
        return render_template('pages/home.html')


@app.route('/venues/<venue_id>', methods=['DELETE'])
def delete_venue(venue_id):

    error = False

    try:
        venue_to_delete = Venue.query.filter_by(id=venue_id).all()[0]
        db.session.delete(venue_to_delete)
        db.session.commit()
    except:
        error = True
    finally:
        db.session.close()

    if error:
        flash('An error occurred. Venue with id #' + str(venue_id) + ' was not deleted.')
        return render_template('pages/home.html')
    else:
        flash('Venue #' + str(venue_id) + ' was successfully deleted!')
        return render_template('pages/home.html')


#  Artists
#  ----------------------------------------------------------------
@app.route('/artists')
def artists():

    artists_query = Artist.query.order_by(Artist.name).all()
    data = [{'id': artist.id, 'name': artist.name} for artist in artists_query]

    return render_template('pages/artists.html', artists=data)


@app.route('/artists/search', methods=['POST'])
def search_artists():

    search_term = request.form.get('search_term', '')
    artists_query = Artist.query.filter(Artist.name.ilike(f'%{search_term}%')).all()

    response = {
        'count': len(artists_query),
        'data': [{'id': artist.id,
                  'name': artist.name,
                  'num_upcoming_shows': Show.query.filter(Show.artist_id == artist.id,
                                                          Show.start_time > datetime.now()).count()}
                 for artist in artists_query]
    }

    return render_template('pages/search_artists.html', results=response,
                           search_term=request.form.get('search_term', ''))


@app.route('/artists/<int:artist_id>')
def show_artist(artist_id):

    try:
        artist = Artist.query.filter_by(id=artist_id).all()[0]
    except:
        return render_template('errors/404.html')

    past_shows = [{
        "venue_id": show.venue.id,
        "venue_name": show.venue.name,
        "venue_image_link": show.venue.image_link,
        "start_time": str(show.start_time)
    } for show in Show.query.filter(Show.artist_id == artist.id, Show.start_time < datetime.now()).all()]

    upcoming_shows = [{
        "venue_id": show.venue.id,
        "venue_name": show.venue.name,
        "venue_image_link": show.venue.image_link,
        "start_time": str(show.start_time)
    } for show in Show.query.filter(Show.artist_id == artist.id, Show.start_time > datetime.now()).all()]

    data = {
        "id": artist.id,
        "name": artist.name,
        "genres": artist.genres,
        "city": artist.city,
        "state": artist.state,
        "phone": artist.phone,
        "website": artist.website,
        "facebook_link": artist.facebook_link,
        "seeking_venue": artist.is_seeking_venue,
        "seeking_description": artist.seeking_description,
        "image_link": artist.image_link,
        "past_shows": past_shows,
        "upcoming_shows": upcoming_shows,
        "past_shows_count": len(past_shows),
        "upcoming_shows_count": len(upcoming_shows),
    }

    return render_template('pages/show_artist.html', artist=data)


#  Update
#  ----------------------------------------------------------------
@app.route('/artists/<int:artist_id>/edit', methods=['GET'])
def edit_artist(artist_id):
    form = ArtistForm()

    try:
        artist = Artist.query.filter_by(id=artist_id).all()[0]
    except:
        return render_template('errors/404.html')

    data = {
        "id": artist.id,
        "name": artist.name,
        "genres": artist.genres,
        "city": artist.city,
        "state": artist.state,
        "phone": artist.phone,
        "website": artist.website,
        "facebook_link": artist.facebook_link,
        "seeking_venue": artist.is_seeking_venue,
        "seeking_description": artist.seeking_description,
        "image_link": artist.image_link
    }

    return render_template('forms/edit_artist.html', form=form, artist=artist)


@app.route('/artists/<int:artist_id>/edit', methods=['POST'])
def edit_artist_submission(artist_id):

    error = False

    try:
        artist = Artist.query.filter_by(id=artist_id).all()[0]

        artist.name = request.form['name']
        artist.city = request.form['city']
        artist.state = request.form['state']
        artist.phone = request.form['phone']
        artist.image_link = request.form['image_link']
        artist.facebook_link = request.form['facebook_link'],
        artist.website = request.form['website']
        artist.genres = request.form.getlist('genres')
        db.session.commit()
    except:
        error = True
    finally:
        db.session.close()

    if error:
        flash('An error occurred. Artist ' + request.form['name'] + ' could not be updated.')
        return redirect(url_for('edit_artist', artist_id=artist_id))
    else:
        flash('Artist ' + request.form['name'] + ' was successfully updated!')
        return redirect(url_for('show_artist', artist_id=artist_id))


@app.route('/venues/<int:venue_id>/edit', methods=['GET'])
def edit_venue(venue_id):
    form = VenueForm()
    try:
        venue = Venue.query.filter_by(id=venue_id).all()[0]
    except:
        return render_template('errors/404.html')

    data = {
        "id": venue.id,
        "name": venue.name,
        "genres": venue.genres,
        "address": venue.address,
        "city": venue.city,
        "state": venue.state,
        "phone": venue.phone,
        "website": venue.website,
        "facebook_link": venue.facebook_link,
        "seeking_talent": venue.is_seeking_talent,
        "seeking_description": venue.seeking_description,
        "image_link": venue.image_link
    }

    return render_template('forms/edit_venue.html', form=form, venue=data)


@app.route('/venues/<int:venue_id>/edit', methods=['POST'])
def edit_venue_submission(venue_id):
    error = False

    try:
        venue = Venue.query.filter_by(id=venue_id).all()[0]

        venue.name = request.form['name']
        venue.city = request.form['city']
        venue.state = request.form['state']
        venue.address = request.form['address']
        venue.phone = request.form['phone']
        venue.image_link = request.form['image_link']
        venue.facebook_link = request.form['facebook_link'],
        venue.website = request.form['website']
        venue.genres = request.form.getlist('genres')
        db.session.commit()
    except:
        error = True
    finally:
        db.session.close()

    if error:
        flash('An error occurred. Venue ' + request.form['name'] + ' could not be updated.')
        return redirect(url_for('edit_venue', venue_id=venue_id))
    else:
        flash('Venue ' + request.form['name'] + ' was successfully updated!')
        return redirect(url_for('show_venue', venue_id=venue_id))


#  Create Artist
#  ----------------------------------------------------------------

@app.route('/artists/create', methods=['GET'])
def create_artist_form():
    form = ArtistForm()
    return render_template('forms/new_artist.html', form=form)


@app.route('/artists/create', methods=['POST'])
def create_artist_submission():

    error = False

    try:
        artist = Artist(name=request.form['name'], city=request.form['city'], state=request.form['state'],
                        phone=request.form['phone'],
                        image_link=request.form['image_link'],
                        facebook_link=request.form['facebook_link'],
                        website=request.form['website'], genres=request.form.getlist('genres'))
        db.session.add(artist)
        db.session.commit()
    except:
        error = True
    finally:
        db.session.close()

    if error:
        flash('An error occurred. Artist ' + request.form['name'] + ' could not be listed.')
        return redirect(url_for('create_artist_form'))
    else:
        flash('Artist ' + request.form['name'] + ' was successfully listed!')
        return render_template('pages/home.html')


#  Shows
#  ----------------------------------------------------------------

@app.route('/shows')
def shows():

    shows_query = Show.query.order_by(Show.start_time).all()
    data = [{'venue_id': show.venue_id,
             'venue_name': show.venue.name,
             'artist_id': show.artist_id,
             'artist_name': show.artist.name,
             'artist_image_link': show.artist.image_link,
             'start_time': str(show.start_time)
             } for show in shows_query]

    return render_template('pages/shows.html', shows=data)


@app.route('/shows/create')
def create_shows():
    # renders form. do not touch.
    form = ShowForm()
    return render_template('forms/new_show.html', form=form)


@app.route('/shows/create', methods=['POST'])
def create_show_submission():

    error = False

    try:
        show = Show(start_time=request.form['start_time'], artist_id=request.form['artist_id'],
                    venue_id=request.form['venue_id'])
        db.session.add(show)
        db.session.commit()
    except:
        error = True
    finally:
        db.session.close()

    if error:
        flash('An error occurred. Show could not be listed.')
        return redirect(url_for('create_show_submission'))
    else:
        flash('The show was successfully listed!')
        return render_template('pages/home.html')


@app.errorhandler(404)
def not_found_error(error):
    return render_template('errors/404.html'), 404


@app.errorhandler(500)
def server_error(error):
    return render_template('errors/500.html'), 500


if not app.debug:
    file_handler = FileHandler('error.log')
    file_handler.setFormatter(
        Formatter('%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]')
    )
    app.logger.setLevel(logging.INFO)
    file_handler.setLevel(logging.INFO)
    app.logger.addHandler(file_handler)
    app.logger.info('errors')

# ----------------------------------------------------------------------------#
# Launch.
# ----------------------------------------------------------------------------#

# Default port:
if __name__ == '__main__':
    app.run()

# Or specify port manually:
'''
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
'''
