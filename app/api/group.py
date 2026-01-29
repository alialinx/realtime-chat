from fastapi import APIRouter, HTTPException, Depends, Query
from app.api.schemas.schemas import CreateGroup, UpdateGroup, ChangeVisibility, AddMember, ChangeRole, UpdateMessageContent
from app.api.tokens.token import current_user
from app.db.db import get_db, close_db

router = APIRouter()


# region GROUPS
@router.get("/groups/public", summary="public groups", tags=["Groups"])
def get_public_groups():
    con, cur = get_db()

    try:
        cur.execute("SELECT * FROM groups WHERE is_private = FALSE ORDER BY id")
        public_groups = cur.fetchall()
        return {"success": True, "message": "public group", "data": public_groups}

    finally:
        close_db(con, cur)

@router.get("/groups/my", summary="my groups", tags=["Groups"])
def get_my_groups(current: dict = Depends(current_user)):
    con, cur = get_db()

    try:
        user_id = current["user_id"]
        cur.execute("SELECT DISTINCT g.* FROM groups g LEFT JOIN group_members gm ON gm.group_id = g.id AND gm.user_id = %s WHERE g.owner_id = %s OR gm.user_id IS NOT NULL", (user_id,user_id))

        my_groups = cur.fetchall()
        return {"success": True, "message": "my group", "data": my_groups}

    finally:
        close_db(con, cur)

@router.get("/groups/{group_id}", summary="get group detail", tags=["Groups"])
def get_group(group_id: int, current: dict = Depends(current_user)):
    con, cur = get_db()

    try:
        user_id = current["user_id"]

        cur.execute("SELECT * FROM groups WHERE id = %s", (group_id,))

        group = cur.fetchone()

        if group.get("is_private") == True and group.get("owner_id") != user_id:
            raise HTTPException(status_code=404, detail="Group not found")

        if group is None:
            raise HTTPException(status_code=404, detail="Group not found")

        return {"success": True, "message": "group found", "data": group}


    finally:
        close_db(con, cur)


@router.post("/groups", summary="create new group", tags=["Groups"])
def create_group(payload: CreateGroup, current: dict = Depends(current_user)):
    con, cur = get_db()

    try:
        user_id = current["user_id"]

        cur.execute("SELECT name FROM groups WHERE owner_id = %s AND name = %s", (user_id, payload.name))
        check_group = cur.fetchone()
        if check_group:
            raise HTTPException(status_code=400, detail="Group already exists")

        cur.execute("INSERT INTO groups(owner_id, name,description) VALUES(%s, %s, %s) RETURNING id", (user_id, payload.name, payload.description))
        row = cur.fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="Group not found")

        role = "admin"
        group_id = row.get("id", None)
        cur.execute("INSERT INTO group_members(user_id, group_id,role) VALUES(%s, %s, %s) ", (user_id,group_id, role))
        con.commit()

        return {"success": True, "message": "group created", "group_id": group_id}


    finally:
        close_db(con, cur)


@router.put("/groups/{group_id}", summary="update my group", tags=["Groups"])
def update_group(payload: UpdateGroup, group_id: int, current: dict = Depends(current_user)):
    con, cur = get_db()
    try:
        user_id = current["user_id"]

        cur.execute("SELECT * FROM groups WHERE id = %s AND owner_id = %s", (group_id, user_id))
        group = cur.fetchone()

        if group is None:
            raise HTTPException(status_code=404, detail="Group not found")

        print("group",group)
        current_name = group.get("name")
        current_desc = group.get("description")
        new_name = payload.name if payload.name is not None else current_name
        new_desc = payload.description if payload.description is not None else current_desc

        cur.execute("UPDATE groups SET name = %s, description = %s WHERE id = %s AND owner_id = %s RETURNING id, name, description", (new_name, new_desc, group_id, user_id))
        updated = cur.fetchone()

        if updated is None:
            raise HTTPException(status_code=404, detail="Group not found")

        con.commit()

        return {"success": True, "message": "group updated", "data": updated}

    finally:
        close_db(con, cur)


@router.delete("/groups/{group_id}", summary="delete my group", tags=["Groups"])
def delete_group(group_id: int, current: dict = Depends(current_user)):
    con, cur = get_db()

    try:
        user_id = current["user_id"]

        cur.execute("DELETE FROM groups WHERE id = %s AND owner_id = %s", (group_id, user_id))

        if cur.rowcount == 0:
            raise HTTPException(status_code=404, detail="Group not found")

        con.commit()

        return {"success": True, "message": "group deleted"}

    finally:
        close_db(con, cur)


@router.put("/groups/{group_id}/visibility", summary="change my group's visibility", tags=["Groups"])
def change_visibility(payload: ChangeVisibility, group_id: int, current: dict = Depends(current_user)):
    con, cur = get_db()

    try:
        user_id = current["user_id"]

        is_private = payload.is_private

        cur.execute("UPDATE groups SET is_private = %s WHERE id = %s AND owner_id = %s RETURNING id, is_private", (is_private, group_id, user_id))
        updated = cur.fetchone()

        if updated is None:
            raise HTTPException(status_code=404, detail="Group not found")

        con.commit()

        return {"success": True, "message": "group updated", "data": updated}

    finally:
        close_db(con, cur)




@router.post("/groups/{group_id}/join", summary="join to group", tags=["Groups"])
def join_to_group(group_id: int, current: dict = Depends(current_user)):
    conn, cur = get_db()
    try:
        user_id = current["user_id"]

        cur.execute("SELECT id, is_private FROM groups WHERE id = %s", (group_id,))
        g = cur.fetchone()
        if g is None:
            raise HTTPException(status_code=404, detail="Group not found")

        if g["is_private"]:
            raise HTTPException(status_code=403, detail="This group is private (invite only)")


        cur.execute("SELECT 1 FROM group_members WHERE group_id = %s AND user_id = %s",(group_id, user_id))
        if cur.fetchone() is not None:
            raise HTTPException(status_code=409, detail="You already joined this group")


        cur.execute("INSERT INTO group_members (group_id, user_id) VALUES (%s, %s)",(group_id, user_id))
        conn.commit()

        return {"success": True, "message": "joined", "group_id": group_id}

    finally:
        close_db(conn, cur)

@router.post("/groups/{group_id}/leave", summary="leave group", tags=["Groups"])
def leave_group(group_id: int, current: dict = Depends(current_user)):
    conn, cur = get_db()
    try:
        user_id = current["user_id"]

        cur.execute("SELECT owner_id FROM groups WHERE id = %s", (group_id,))
        g = cur.fetchone()
        if g is None:
            raise HTTPException(status_code=404, detail="Group not found")

        if g["owner_id"] == user_id:
            raise HTTPException(status_code=403,detail="Owner cannot leave the group. Transfer ownership or delete the group.")

        cur.execute("SELECT 1 FROM group_members WHERE group_id = %s AND user_id = %s",(group_id, user_id))
        if cur.fetchone() is None:
            raise HTTPException(status_code=409, detail="You are not a member of this group")

        cur.execute("DELETE FROM group_members WHERE group_id = %s AND user_id = %s",(group_id, user_id))
        conn.commit()

        return {"success": True, "message": "left", "group_id": group_id}

    finally:
        close_db(conn, cur)

# endregion GROUPS






# region GROUP MEMBERS

@router.get("/groups/{group_id}/members", summary="get my group's members", tags=["Group Members"])
def get_group_members(group_id: int, current: dict = Depends(current_user)):
    con, cur = get_db()

    try:
        user_id = current["user_id"]

        cur.execute("SELECT 1 FROM groups WHERE id = %s", (group_id,))
        check_group = cur.fetchone()

        if check_group is None:
            raise HTTPException(status_code=404, detail="Group not found")

        cur.execute("SELECT 1 FROM group_members WHERE group_id = %s AND user_id= %s", (group_id, user_id))

        if cur.fetchone() is None:
            raise HTTPException(status_code=403, detail="You are not a member of this group")

        cur.execute("SELECT user_id, role, joined_at, is_mute FROM group_members WHERE group_id = %s ORDER BY joined_at", (group_id,))

        members = cur.fetchall()
        return {"success": True, "message": "group members", "members": members}



    finally:
        close_db(con, cur)


@router.post("/groups/{group_id}/members", summary="add member", tags=["Group Members"])
def add_member(group_id: int, payload: AddMember, current: dict = Depends(current_user)):
    con, cur = get_db()

    try:
        user_id = current["user_id"]

        cur.execute("SELECT 1 FROM groups WHERE id = %s AND owner_id = %s", (group_id, user_id))
        if cur.fetchone() is None:
            raise HTTPException(status_code=403, detail="You are not a owner of this group")

        cur.execute("SELECT 1 FROM users WHERE id= %s", (payload.member_id,))
        check_user = cur.fetchone()
        if not check_user:
            raise HTTPException(status_code=404, detail="User not found")

        cur.execute("SELECT 1 FROM group_members WHERE group_id = %s AND user_id = %s", (group_id, payload.member_id))
        exist_member = cur.fetchone()
        if exist_member:
            raise HTTPException(status_code=409, detail="User is already a member of this group")

        cur.execute("INSERT INTO group_members (group_id, user_id, role) VALUES (%s, %s, %s)", (group_id, payload.member_id, payload.role))
        con.commit()
        return {"success": True, "message": "member added"}

    finally:
        close_db(con, cur)


@router.delete("/groups/{group_id}/members/{member_id}", summary="  Delete member in groups", tags=["Group Members"])
def delete_member(group_id: int, member_id: int, current: dict = Depends(current_user)):
    con, cur = get_db()

    try:
        user_id = current["user_id"]

        cur.execute("SELECT 1 FROM groups WHERE id = %s AND owner_id = %s", (group_id, user_id))
        if cur.fetchone() is None:
            raise HTTPException(status_code=403, detail="You are not a owner of this group")

        cur.execute("SELECT 1 FROM group_members WHERE group_id = %s AND user_id = %s", (group_id, member_id))
        check_member = cur.fetchone()
        if not check_member:
            raise HTTPException(status_code=404, detail="Member not found in this group")

        cur.execute("DELETE FROM group_members WHERE group_id = %s AND user_id = %s", (group_id, member_id))
        con.commit()
        return {"success": True, "message": "member deleted"}

    finally:
        close_db(con, cur)


@router.delete("/groups/{group_id}/members/me", summary="leave this group", tags=["Group Members"])
def leaving_to_group(group_id: int, current: dict = Depends(current_user)):
    con, cur = get_db()

    try:

        user_id = current["user_id"]

        cur.execute("SELECT 1 FROM groups WHERE group_id = %s AND owner_id = %s", (group_id,user_id))
        check_owner = cur.fetchone()
        if check_owner:
            raise HTTPException(403, "You can't leave because you're the group leader")

        cur.execute("SELECT 1 FROM group_members WHERE group_id = %s AND user_id = %s", (group_id, user_id))
        check_member = cur.fetchone()
        if not check_member:
            raise HTTPException(status_code=403, detail="You don't belong to this group")

        cur.execute("DELETE FROM group_members WHERE group_id = %s AND user_id = %s", (group_id, user_id))
        con.commit()
        return {"success": True, "message": "You left the group"}



    finally:
        close_db(con, cur)


@router.put("/groups/{group_id}/members/{member_id}/role", summary="Update member role in group", tags=["Group Members"])
def change_member_role(group_id: int, member_id: int, payload: ChangeRole, current: dict = Depends(current_user)):
    conn, cur = get_db()
    try:
        user_id = current["user_id"]

        cur.execute("SELECT owner_id FROM groups WHERE id = %s", (group_id,))
        g = cur.fetchone()
        if g is None:
            raise HTTPException(status_code=404, detail="Group not found")

        owner_id = g["owner_id"]


        if user_id != owner_id:
            raise HTTPException(status_code=403, detail="Only the owner can change member roles")


        if member_id == owner_id:
            raise HTTPException(status_code=400, detail="Owner role cannot be changed")


        if payload.role not in ("admin", "member"):
            raise HTTPException(status_code=400, detail="Invalid role. Allowed: admin, member")


        cur.execute("SELECT role FROM group_members WHERE group_id = %s AND user_id = %s",(group_id, member_id))
        m = cur.fetchone()
        if m is None:
            raise HTTPException(status_code=404, detail="Member not found in this group")


        if m["role"] == payload.role:
            return {"success": True, "message": "role unchanged"}

        cur.execute("UPDATE group_members SET role = %s WHERE group_id = %s AND user_id = %s",(payload.role, group_id, member_id))
        conn.commit()
        return {"success": True, "message": "member role updated"}

    finally:
        close_db(conn, cur)


@router.put("/groups/{group_id}/members/{member_id}/mute", summary="  Mute member in groups", tags=["Group Members"])
def mute_member(group_id: int, member_id: int, current: dict = Depends(current_user)):
    con, cur = get_db()

    try:
        user_id = current["user_id"]

        cur.execute("SELECT 1 FROM groups WHERE id = %s AND owner_id = %s", (group_id, user_id))
        if cur.fetchone() is None:
            raise HTTPException(status_code=403, detail="You are not a owner of this group")

        cur.execute("SELECT 1 FROM group_members WHERE group_id = %s AND user_id = %s", (group_id, member_id))
        check_member = cur.fetchone()
        if not check_member:
            raise HTTPException(status_code=404, detail="Member not found in this group")

        cur.execute("UPDATE group_members SET is_mute = true WHERE group_id = %s AND user_id = %s ", (group_id, member_id))
        con.commit()
        return {"success": True, "message": "member has been muted"}

    finally:
        close_db(con, cur)


@router.put("/groups/{group_id}/members/{member_id}/unmute", summary="  Unmute member in groups", tags=["Group Members"])
def unmute_member(group_id: int, member_id: int, current: dict = Depends(current_user)):
    con, cur = get_db()

    try:
        user_id = current["user_id"]

        cur.execute("SELECT 1 FROM groups WHERE id = %s AND owner_id = %s", (group_id, user_id))
        if cur.fetchone() is None:
            raise HTTPException(status_code=403, detail="You are not a owner of this group")

        cur.execute("SELECT 1 FROM group_members WHERE group_id = %s AND user_id = %s", (group_id, member_id))
        check_member = cur.fetchone()
        if not check_member:
            raise HTTPException(status_code=404, detail="Member not found in this group")

        cur.execute("UPDATE group_members SET is_mute = false WHERE group_id = %s AND user_id = %s ", (group_id, member_id))
        con.commit()
        return {"success": True, "message": "member has been unmuted"}

    finally:
        close_db(con, cur)

@router.put("/groups/{group_id}/members/me/read",summary="mark group as read",tags=["Group Members"])
def mark_group_as_read(group_id: int, current: dict = Depends(current_user)):
    con, cur = get_db()
    try:
        user_id = current["user_id"]
        cur.execute("SELECT 1 FROM group_members WHERE group_id = %s AND user_id = %s",(group_id, user_id))
        if cur.fetchone() is None:
            raise HTTPException(status_code=403, detail="You are not a member of this group")

        cur.execute("""UPDATE group_members SET last_read_at = now() WHERE group_id = %s AND user_id = %s """, (group_id, user_id))

        con.commit()
        return {"success": True, "message": "group marked as read"}

    finally:
        close_db(con, cur)


# endregion GROUP MEMBERS

# region GROUP MESSAGES

@router.get("/groups/{group_id}/messages", summary="Get group messages",tags=["Group Messages"])
def get_group_messages(group_id: int,page: int = 1,limit: int = 20, current: dict = Depends(current_user)):

    con, cur = get_db()

    try:
        user_id = current["user_id"]

        cur.execute("SELECT 1 FROM group_members WHERE group_id = %s AND user_id = %s", (group_id, user_id))
        if cur.fetchone() is None:
            raise HTTPException(status_code=403, detail="You are not a member of this group")

        offset = (page - 1) * limit

        cur.execute("SELECT * FROM group_messages WHERE group_id = %s ORDER BY created_at DESC LIMIT %s OFFSET %s ", (group_id,limit,offset))
        messages = cur.fetchall()

        return {"success": True,"message": "messages fetched","page": page,"limit": limit,"count": len(messages),"data": messages}

    finally:
        close_db(con, cur)



@router.delete("/groups/{group_id}/messages/{message_id}", summary = "Delete Message", tags=["Group Messages"])
def delete_message(group_id: int, message_id: int, current: dict = Depends(current_user)):


    con, cur = get_db()

    try:
        user_id = current["user_id"]

        cur.execute("SELECT 1 FROM group_members WHERE group_id = %s AND user_id = %s", (group_id, user_id))
        if cur.fetchone() is None:
            raise HTTPException(status_code=403, detail="You are not a member of this group")


        cur.execute("SELECT sender_id FROM group_messages WHERE group_id = %s AND id = %s",(group_id, message_id))
        row = cur.fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="Message not found")

        if row[0] != user_id:
            raise HTTPException(status_code=403, detail="You cannot delete someone else's message")



        cur.execute("DELETE FROM group_messages WHERE group_id = %s AND id = %s AND sender_id = %s ", (group_id, message_id, user_id))
        con.commit()
        return {"success": True, "message": "message deleted"}


    finally:
        close_db(con, cur)

@router.put("/groups/{group_id}/messages/{message_id}", summary="Update Message",tags=["Group Messages"])
def update_message(payload: UpdateMessageContent ,group_id: int, message_id: int, current: dict = Depends(current_user)):

    con, cur = get_db()

    try:
        user_id = current["user_id"]

        cur.execute("SELECT 1 FROM group_members WHERE group_id = %s AND user_id = %s", (group_id, user_id))
        if cur.fetchone() is None:
            raise HTTPException(status_code=403, detail="You are not a member of this group")

        cur.execute("SELECT 1 FROM group_messages WHERE group_id = %s AND id = %s AND sender_id =%s", (group_id, message_id, user_id))
        check_message = cur.fetchone()
        if not check_message:
            raise HTTPException(status_code=404, detail="This message is not yours. Therefore, you cannot update it.")


        cur.execute("UPDATE group_messages SET content = %s  WHERE group_id = %s AND id = %s AND sender_id = %s", (payload.content, group_id, message_id, user_id))
        con.commit()

        return {"success": True, "message": "message updated"}



    finally:
        close_db(con, cur)







# endregion GROUP MESSAGES