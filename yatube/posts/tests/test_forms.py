import shutil
import tempfile
from http import HTTPStatus

from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from ..models import Group, Post, User, Comment

TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class PostCreateFormTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        small_gif = (
            b'\x47\x49\x46\x38\x39\x61\x02\x00'
            b'\x01\x00\x80\x00\x00\x00\x00\x00'
            b'\xFF\xFF\xFF\x21\xF9\x04\x00\x00'
            b'\x00\x00\x00\x2C\x00\x00\x00\x00'
            b'\x02\x00\x01\x00\x00\x02\x02\x0C'
            b'\x0A\x00\x3B'
        )
        uploaded = SimpleUploadedFile(
            name='small.gif',
            content=small_gif,
            content_type='image/gif'
        )
        cls.user = User.objects.create_user(username='noname')
        cls.guest_client = Client()
        cls.authorized_client = Client()
        cls.authorized_client.force_login(cls.user)
        cls.group = Group.objects.create(
            title='Test group',
            slug='test-slug',
            description='Test description'
        )

        cls.post_edit = Post.objects.create(
            author=cls.user,
            text='Text editing',
            group=cls.group,
            image=uploaded,
        )

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        self.client = Client()
        self.client.force_login(self.user)

    def test_create_post(self):
        """Проверка создания записи в БД, при отправке валидной формы."""
        post_count = Post.objects.count()

        form_fields = {
            'text': 'Text',
            'group': self.group.pk,
            'image': self.post_edit.image
        }
        response = self.authorized_client.post(
            reverse('posts:post_create'),
            data=form_fields,
            follow=True
        )
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertRedirects(response, reverse(
            'posts:profile',
            kwargs={'username': self.user.username}
        ))
        self.assertEqual(Post.objects.count(), post_count + 1)
        self.assertEqual(
            Post.objects.latest('pub_date').text,
            form_fields['text']
        )
        self.assertEqual(
            Post.objects.latest('pub_date').author.username,
            self.user.username)

        self.assertEqual(Post.objects.latest('pub_date').group, self.group)

    def test_edit_post(self):
        """Проверка изменения записи в БД,
           при отправке валидной формы со страницы редактирования.
        """
        form_data = {
            'group': self.group.pk,
            'text': 'Edit text',
        }

        self.client.post(
            reverse('posts:post_edit', args=[self.post_edit.pk]),
            data=form_data,
            follow=True
        )
        text_edit = Post.objects.get(pk=self.post_edit.pk).text
        self.assertMultiLineEqual(
            text_edit,
            'Edit text',
            f'Пост "{self.post_edit.text}" автора "{self.user}",'
            f' с ID "{self.post_edit.pk}", не редактируется.'
        )


class CommentFormTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create(username='noname')
        cls.guest_client = Client()
        cls.authorized_client = Client()
        cls.authorized_client.force_login(cls.user)
        cls.group_test = Group.objects.create(
            title='Test group',
            slug='test-slug',
            description='Test description'
        )
        cls.post = Post.objects.create(
            text='Text',
            group=cls.group_test,
            author=cls.user,
        )
        cls.comment_test = Comment.objects.create(
            text='Text comment',
            post=cls.post,
            author=cls.user
        )

    def test_authorized_comment(self):
        """Проверка того, что авторизованный пользователь может добавить
            комментарий.
        """
        comments_count = Comment.objects.count()
        form_data = {
            'text': 'Text'
        }
        self.authorized_client.post(
            reverse('posts:add_comment', kwargs={'post_id': self.post.pk}),
            data=form_data
        )
        self.assertEqual(Comment.objects.count(), comments_count + 1)

    def test_guest_comment(self):
        """Проверка того, что неавторизованный пользователь не может добавить
            комментарий.
        """
        comments_count = Comment.objects.count()

        form_data = {
            'text': 'Text'
        }
        response = self.guest_client.post(
            reverse('posts:add_comment', kwargs={'post_id': self.post.pk}),
            data=form_data
        )
        self.assertEqual(Comment.objects.count(), comments_count)
        redirect = "%s?next=%s" % (
            reverse('users:login'),
            reverse('posts:add_comment', kwargs={'post_id': self.post.pk})
        )
        self.assertRedirects(response, redirect)
