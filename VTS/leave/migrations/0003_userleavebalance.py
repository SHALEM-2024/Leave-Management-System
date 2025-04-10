# Generated by Django 5.1.7 on 2025-04-10 07:03

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('leave', '0002_remove_grant_employee_grant_employee_category_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='UserLeaveBalance',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('allocated_hours', models.IntegerField(blank=True, help_text='Total allocated leave hours for this category.', null=True)),
                ('remaining_hours', models.IntegerField(blank=True, help_text='Remaining leave hours for this category.', null=True)),
                ('category', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='user_leave_balances', to='leave.category')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='leave_balances', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'unique_together': {('user', 'category')},
            },
        ),
    ]
