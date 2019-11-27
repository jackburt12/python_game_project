from items import GetItem, Weapon, Armour, Consumable
from inventory import Inventory
from flask import Flask, render_template, url_for, request, redirect, jsonify
from flask_sqlalchemy import SQLAlchemy

MOVEMENT_ENERGY_COST = 5
MOVEMENT_HUNGER_COST = 3
ENERGY_MESSAGE = "You fail to muster to strength to take even one more step, best find somewhere to sleep for the night..."
BOUNDARY_MESSAGE = "There are towering cliffs in front of you, you'll have to choose another direction..."

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///data.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

class Player(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(32), nullable=False)
    health = db.Column(db.Integer, default=100)
    hunger = db.Column(db.Integer, default=81)
    energy = db.Column(db.Integer, default=100)
    location_x = db.Column(db.Integer, default=2)
    location_y = db.Column(db.Integer, default=3)

    def __repr__(self):
        return '<Task %r>' % self.id

class Item(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    item_id = db.Column(db.String(32), nullable=False)
    item_type = db.Column(db.String(8), nullable=False)
    quantity = db.Column(db.Integer, default=1)

    def __repr__(self):
        return '<Task %r>' % self.id

@app.route("/", methods=['POST', 'GET'])
def index():

    if request.method=='POST':
        if 'new_game' in request.form:
            try:
                clear_database()
                return render_template("create-character.html")
            except:
                return 'There was an issue starting a new game!'
        elif 'create_character' in request.form:
            player_name = request.form['name']
            player = Player(name=player_name)

            #this is how you add an item to the player
            #you must lookup the item you wish to add in its relevant csv file
            #whichever line it is in the csv file is what the item_id should be
            swiss = Item(item_id=1, item_type="Weapon")
            nuts = Item(item_id=1, item_type="Consumable")
            nuts.quantity = 3
            try:
                clear_database()
                db.session.add(player)
                db.session.add(swiss)
                db.session.add(nuts)
                db.session.commit()
                return render_template("game-interface.html", player=player, items=load_inventory())
            except:
                return 'There was an issue creating the player'
        elif 'sleep' in request.form:
            current_player = Player.query.first()
            current_player.energy = 100
            db.session.commit()
            return render_template("game-interface.html", player=current_player, items=load_inventory())

    else:
        current_player = Player.query.first()
        if current_player is None:
            return render_template("create-character.html")
        else:
            return render_template("game-interface.html", player=current_player, items=load_inventory())

@app.route("/north")
def north():
    return move_square("north")

@app.route("/east")
def east():
    return move_square("east")

@app.route("/south")
def south():
    return move_square("south")


@app.route("/west")
def west():
    return move_square("west")

@app.route("/sleep")
def sleep():
    player = Player.query.first()
    player.energy = 100
    db.session.commit()

    return jsonify(energy=player.energy)

@app.route("/item/<item>")
def item(item):
    player = Player.query.first()

    used_item = select_item(item)
    if used_item.item_type == "Consumable":
        consumable = GetItem(used_item.item_type, used_item.item_id)

        old_stat = 0
        amount = 0
        print(consumable.effect)
        if consumable.effect == "Hunger":
            if player.hunger <100:
                old_stat = player.hunger
                print ("hunger restored by "+ consumable.amount)
                player.hunger = player.hunger + int(consumable.amount)
                if player.hunger > 100:
                    player.hunger = 100
                db.session.commit()
                amount = player.hunger - old_stat
        elif consumable.effect == "Health":
            if player.health <100:
                old_stat = player.health
                print ("health restored by "+ consumable.amount)
                player.health = player.health + int(consumable.amount)
                if player.health > 100:
                    player.health = 100
                db.session.commit()
                amount = player.health - old_stat
        elif consumable.effect == "Energy":
            if player.energy <100:
                old_stat = player.energy
                print ("energy restored by "+ consumable.amount)
                player.energy = player.energy + int(consumable.amount)
                if player.energy > 100:
                    player.energy = 100
                db.session.commit()
                amount = player.energy - old_stat
        if amount is 0:
            print("Amount is 0")
            return jsonify(error="Consumable would have no effect")
        else:
            return jsonify(hunger=player.hunger, health=player.health, energy=player.energy, effect=consumable.effect, amount=amount, quantity = decrease_quantity(used_item))
    else:
        return "nothing"
    #return render_template('user_popup.html', user=user)


def load_inventory():
    items_raw = Item.query.all()
    items_parsed = []
    for item in items_raw:
        new_item = GetItem(item.item_type, item.item_id)
        new_item.quantity = item.quantity
        items_parsed.append(new_item)

    damage = 0
    armour = 0

    for item in items_parsed:
        print(type(item))
        if isinstance(item, Weapon):
            print(item.damage)
            if int(item.damage) > int(damage):
                damage = item.damage
        elif isinstance(item, Armour):
            if int(item.protection) > int(armour):
                armour = item.protection

    return Inventory(items_parsed, damage, armour)

def select_item(item_name):
    items_raw = Item.query.all()
    for item in items_raw:
        new_item = GetItem(item.item_type, item.item_id)
        if new_item.name == item_name:
            return item


def decrease_quantity(item):
    item.quantity = item.quantity-1
    if item.quantity <= 0:
        db.session.delete(item)
    db.session.commit()
    return item.quantity


def move_square(direction):
    player = Player.query.first()

    if player.energy < MOVEMENT_ENERGY_COST:
        return jsonify(error=ENERGY_MESSAGE)

    else:
        if direction is 'north':
            if (player.location_y>=11):
                #player reached bound
                return jsonify(error=BOUNDARY_MESSAGE)
            else:
                player.location_y = player.location_y + 1

        elif direction is 'east':
            if (player.location_x>=24):
                return jsonify(error=BOUNDARY_MESSAGE)
            else:
                player.location_x = player.location_x + 1

        elif direction is 'south':
            if (player.location_y<= 0):
                return jsonify(error=BOUNDARY_MESSAGE)
            else:
                player.location_y = player.location_y - 1

        elif direction is 'west':
            if (player.location_x<=0):
                return jsonify(error=BOUNDARY_MESSAGE)
            else:
                player.location_x = player.location_x - 1

    starving = "false"
    player.energy = player.energy - MOVEMENT_ENERGY_COST
    player.hunger = player.hunger - MOVEMENT_HUNGER_COST
    if player.hunger < 0:
        player.hunger = 0
        player.health = player.health - 2
        starving = "true"
    db.session.commit()
    return jsonify(location="["+str(player.location_x)+", "+str(player.location_y)+"]", hunger=player.hunger, energy=player.energy, starving=starving)

def clear_database():
    db.session.query(Item).delete()
    db.session.query(Player).delete()
    db.session.commit()

if __name__ == "__main__":
    app.run(debug=True)
