from fastapi import FastAPI, HTTPException, Depends, File, UploadFile, Form
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session, aliased
from sqlalchemy.sql import exists, and_
from models import init_db, SessionLocal, Item, Tag, item_tags, fill_states
from schemas import ItemCreate, ItemUpdate, ItemResponse
from typing import List
import shutil
from PIL import Image
import uuid
from pathlib import Path
import logging

app = FastAPI(debug=True)
init_db()
fill_states()

logger = logging.getLogger("uvicorn")

base_dir = Path(__file__).parent.absolute()  
static_files_dir = base_dir / "static"
static_files_dir.mkdir(exist_ok=True)

app.mount("/static", StaticFiles(directory=str(static_files_dir)), name="static")

def resize_image(image_path, output_path, width, height):
    with Image.open(image_path) as img:
        # Resize the image
        img = img.resize((width, height), Image.LANCZOS)
        # Save the resized image
        img.save(output_path)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@app.post("/items/", response_model=ItemCreate)
def create_item(name: str = Form(...),
                comment: str = Form(None),
                label_id: int = Form(None),
                parent_item_id: int = Form(None),
                image: UploadFile = File(None),
                db: Session = Depends(get_db)):
    item_data = {"name": name, "comment": comment, "label_id": label_id, "parent_item_id": parent_item_id}
    if image and image.filename:
        file_extension = Path(image.filename).suffix
        if file_extension not in [".jpg", ".jpeg", ".png"]:
            raise HTTPException(status_code=400, detail="Invalid file type")
        random_filename = f"{uuid.uuid4()}{file_extension}"
        image_lg_path = static_files_dir / random_filename
        output_location = static_files_dir / f"resized_{random_filename}"
        with open(image_lg_path, "wb") as buffer:
            shutil.copyfileobj(image.file, buffer)
        try:
            resize_image(image_lg_path, output_location, 80, 80)
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

        item_data["image_lg_path"] = image_lg_path.relative_to(base_dir).as_posix()
        item_data["image_sm_path"] = output_location.relative_to(base_dir).as_posix()

    db_item = Item(**item_data)
    db.add(db_item)
    try:
        db.commit()
        db.refresh(db_item)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

    return db_item

# get all items
@app.get("/items/", response_model=List[ItemResponse])
def get_all_items(db: Session = Depends(get_db)):
    items = db.query(Item).all()
    return items

# update item
@app.put("/items/{item_id}", response_model=ItemUpdate)
def update_item(item_id: int, item_data: ItemUpdate, db: Session = Depends(get_db)):
    db_item = db.query(Item).filter(Item.item_id == item_id).first()
    if not db_item:
        raise HTTPException(status_code=404, detail="Item not found")
    try:
        for var, value in vars(item_data).items():
            if value is not None:
                setattr(db_item, var, value)
        db.commit()
        db.refresh(db_item)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    return db_item

# get item via ID
@app.get("/items/{item_id}")
def read_item(item_id: int, db: Session = Depends(get_db)):
    db_item = db.query(Item).filter(Item.id == item_id).first()
    if db_item is None:
        raise HTTPException(status_code=404, detail="Item not found")
    return db_item

# get item children
@app.get("/items/children/{item_id}", response_model=List[ItemResponse])
def get_item_children(item_id: int, db: Session = Depends(get_db)):
    child_alias = aliased(Item)
    has_children = exists().where(child_alias.parent_item_id == Item.item_id).label("has_children")
    has_children_none = exists().where(child_alias.parent_item_id == None).label("has_children")
    if item_id is None or item_id == 0:
        children = db.query(Item, has_children_none).filter(Item.parent_item_id == None).all()
        print(f"child count: {len(children)}")
        if not children:
            raise HTTPException(status_code=404, detail="No Top Items found")
        children = add_has_children_field(children)
        return children
    children = db.query(Item, has_children).filter(Item.parent_item_id == item_id).all()
    if not children:
        raise HTTPException(status_code=404, detail="No children found for this item")
    # check if children have min one child
    children = add_has_children_field(children)
    return children

@app.delete("/items/{item_id}")
def delete_item(item_id: int, db: Session = Depends(get_db)):
    db_item = db.query(Item).filter(Item.id == item_id).first()
    if db_item is None:
        raise HTTPException(status_code=404, detail="Item not found")
    db.delete(db_item)
    db.commit()
    return {"detail": "Item deleted"}

@app.get("/items/{tag_name}")
def get_items_by_tag(tag_name: str, db: Session = Depends(get_db)):
    items = db.query(Item).join(Item.tags).filter(Tag.tag_name == tag_name).all()
    if not items:
        raise HTTPException(status_code=404, detail="Item not found")
    return items

@app.post("/tags/")
def create_tag(tag_name: str, db: Session = Depends(get_db)):
    db_tag = Tag(tag_name=tag_name)
    db.add(db_tag)
    db.commit()
    db.refresh(db_tag)
    return db_tag

@app.delete("/tags/{tag_id}")
def delete_tag(tag_id: int, db: Session = Depends(get_db)):
    # Delete associations in item_tags junction table
    db.query(item_tags).filter(item_tags.c.tag_id == tag_id).delete(synchronize_session=False)

    # Delete the tag itself
    db_tag = db.query(Tag).filter(Tag.tag_id == tag_id).first()
    if db_tag is None:
        raise HTTPException(status_code=404, detail="Tag not found")
    db.delete(db_tag)
    db.commit()
    return {"detail": "Tag deleted"}

def add_has_children_field(result_list):
    if len(result_list[0]) != 2:
        raise HTTPException(status_code=500, detail="Database returns not ITEM, has_children")
    new_items = []
    for item_and_children in result_list:
        item = item_and_children[0]
        has_children = item_and_children[1]
        item.has_children = has_children
        new_items.append(item)
    return new_items
