from __future__ import annotations

import discord 
from typing import Optional 

from copy import deepcopy
from typing import TYPE_CHECKING, Optional, Any, TypeAlias

import discord
from discord import ButtonStyle
from discord.ext import commands

from discord import ui 

from .modals import (
    AddFieldModal,
    EditAuthorModal,
    EditEmbedModal,
    EditFieldModal,
    EditFooterModal,
    EditWithModalButton,
)

class Embed(discord.Embed):
    def __bool__(self) -> bool:
        return any(
            (
                self.title,
                self.url,
                self.description,
                self.fields,
                self.timestamp,
                self.author,
                self.thumbnail,
                self.footer,
                self.image,
            )
        )

class DeleteButton(discord.ui.Button['EmbedEditor']):
    async def callback(self, interaction):
        if interaction.message:
            await interaction.message.delete()
        await interaction.response.send_message(
            'Done!\n*This message goes away in 10 seconds*\n*You can use this to recover your progress.*',
            view=UndoView(self.view),  # type: ignore
            delete_after=10,
            ephemeral=True,
        )

class FieldSelectorView(ui.View):
    def __init__(self, parent_view: EmbedEditor):
        self.parent = parent_view
        super().__init__(timeout=300, bot=parent_view.bot)
        self.update_options()

    def update_options(self):
        self.pick_field.options = []
        for i, field in enumerate(self.parent.embed.fields):
            self.pick_field.add_option(label=f"{i + 1}) {(field.name or '')[0:95]}", value=str(i))

    @discord.ui.select(placeholder='Select a field to delete.')
    async def pick_field(self, interaction, select):
        await self.actual_logic(interaction, select)

    @discord.ui.button(label='Go back')
    async def cancel(self, interaction, button):
        await interaction.response.edit_message(view=self.parent)
        self.stop()

    async def actual_logic(self, interaction, select) -> None:
        raise NotImplementedError('Child classes must overwrite this method.')
    
class DeleteFieldWithSelect(FieldSelectorView):
    async def actual_logic(self, interaction, select):
        index = int(select.values[0])
        self.parent.embed.remove_field(index)
        await self.parent.update_buttons()
        await interaction.response.edit_message(embed=self.parent.current_embed, view=self.parent)
        self.stop()


class EditFieldSelect(FieldSelectorView):
    async def actual_logic(self, interaction, select):
        index = int(select.values[0])
        self.parent.timeout = 600
        await interaction.response.send_modal(EditFieldModal(self.parent, index))


class EmbedEditor(ui.View):
    def __init__(self, bot, owner: discord.Member, timeout: Optional[float] = 600, embed: Optional[discord.Embed] = None):
        self.owner: discord.Member = owner
        self.embed = Embed() if embed is None else embed 
        self.bot = bot 
        self.ready = False 
        self.message: Optional[discord.Message] = None
        super().__init__(timeout=timeout)
        self.clear_items()
        self.add_items()

    @staticmethod
    def shorten(_embed: discord.Embed):
        embed = Embed.from_dict(deepcopy(_embed.to_dict()))
        while len(embed) > 6000 and embed.fields:
            embed.remove_field(-1)
        if len(embed) > 6000 and embed.description:
            embed.description = embed.description[: (len(embed.description) - (len(embed) - 6000))]
        return embed

    @property
    def current_embed(self) -> discord.Embed:
        if self.embed:
            if len(self.embed) < 6000:
                return self.embed
            else:
                return self.shorten(self.embed)

    async def interaction_check(self, interaction):
        if interaction.user == self.owner:
            return True
        await interaction.response.send_message('This is not your menu.', ephemeral=True)

    def add_items(self):
        """This is done this way because if not, it would get too cluttered."""
        # Row 1
        self.add_item(discord.ui.Button(label='Edit:', style=ButtonStyle.blurple, disabled=True))
        self.add_item(EditWithModalButton(EditEmbedModal, label='Embed', style=ButtonStyle.blurple))
        self.add_item(EditWithModalButton(EditAuthorModal, row=0, label='Author', style=ButtonStyle.blurple))
        self.add_item(EditWithModalButton(EditFooterModal, row=0, label='Footer', style=ButtonStyle.blurple))
        self.add_item(DeleteButton(emoji='\N{WASTEBASKET}', style=ButtonStyle.red))
        # Row 2
        self.add_item(discord.ui.Button(row=1, label='Fields:', disabled=True, style=ButtonStyle.blurple))
        self.add_fields = EditWithModalButton(AddFieldModal, row=1, emoji='\N{HEAVY PLUS SIGN}', style=ButtonStyle.green)
        self.add_item(self.add_fields)
        self.add_item(self.remove_fields)
        self.add_item(self.edit_fields)
        self.add_item(self.reorder)
        # Row 3
        self.add_item(self.send)
        # Row 4
        self.character_count = discord.ui.Button(row=3, label='0/6,000 Characters', disabled=True)
        self.add_item(self.character_count)
        self.fields_count = discord.ui.Button(row=3, label='0/25 Total Fields', disabled=True)
        self.add_item(self.fields_count)

    async def update_buttons(self):
        fields = len(self.embed.fields)
        if fields > 25:
            self.add_fields.disabled = True
        else:
            self.add_fields.disabled = False
        if not fields:
            self.remove_fields.disabled = True
            self.edit_fields.disabled = True
            self.reorder.disabled = True
        else:
            self.remove_fields.disabled = False
            self.edit_fields.disabled = False
            self.reorder.disabled = False
        if self.embed:
            if len(self.embed) <= 6000:
                self.send.style = ButtonStyle.green
            else:
                self.send.style = ButtonStyle.red
        else:
            self.send.style = ButtonStyle.red

        self.character_count.label = f"{len(self.embed)}/6,000 Characters"
        self.fields_count.label = f"{len(self.embed.fields)}/25 Total Fields"

    @discord.ui.button(row=1, emoji='\N{HEAVY MINUS SIGN}', style=ButtonStyle.red, disabled=True)
    async def remove_fields(self, interaction, button):
        await interaction.response.edit_message(view=DeleteFieldWithSelect(self))

    @discord.ui.button(row=1, emoji="\U0001f4dd", disabled=True, style=ButtonStyle.green)
    async def edit_fields(self, interaction, button):
        await interaction.response.edit_message(view=EditFieldSelect(self))

    @discord.ui.button(row=1, label='Reorder', style=ButtonStyle.blurple, disabled=True)
    async def reorder(self, interaction, button):
        return await interaction.response.send_message(
            f'This function is currently unavailable.\nPlease use and edit the `index`',
            ephemeral=True,
        )

    @discord.ui.button(label='Submit', row=2, style=ButtonStyle.red)
    async def send(self, interaction, button):
        if not self.embed:
            return await interaction.response.send_message('Your embed is empty!', ephemeral=True)
        elif len(self.embed) > 6000:
            return await interaction.response.send_message(
                'You have exceeded the embed character limit (6000)', ephemeral=True
            )
        
        await interaction.response.defer()
        await interaction.delete_original_response()
        self.ready = True
        self.stop()

    async def on_timeout(self) -> None:
        if self.message:
            if self.embed:
                await self.message.edit(view=None)
            else:
                await self.message.delete()