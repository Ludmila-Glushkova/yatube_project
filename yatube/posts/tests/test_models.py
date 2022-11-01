from django.test import TestCase

from ..models import Group, Post, User

SLICE_POST = 15


class PostModelTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='noname')
        cls.group = Group.objects.create(
            title='Test group',
            slug='test-slug',
            description='Test description'
        )
        cls.post = Post.objects.create(
            author=cls.user,
            text='Test text',
            group=cls.group
        )

    def test_correct_str(self):
        """Проверка корректной работы метода __str__."""
        task = PostModelTest.post
        model_repr = task.__str__()
        self.assertEqual(model_repr, task.text[:SLICE_POST],
                         f'Убедитесь, что у модели Post метод __str__'
                         f' возвращает {Post.__name__}.text[:{SLICE_POST}]'
                         )

        task = PostModelTest.group
        model_repr = task.__str__()
        self.assertEqual(model_repr, task.title,
                         f"Убедитесь, что у модели Group метод __str__"
                         f' возвращает значение из поля "title" {task.title}'
                         )

    def test_verbose_name(self):
        """Проверка verbose_name у модели Post."""
        task = PostModelTest.post
        dict_verbose_name = {
            'author': 'Автор',
            'text': 'Текст поста',
            'group': 'Группа',
        }
        for field, value in dict_verbose_name.items():
            with self.subTest(field=field):
                self.assertEqual(
                    task._meta.get_field(field).verbose_name, value
                )

    def test_help_text(self):
        """Проверка help_text у модели Post."""
        task = PostModelTest.post
        dict_help_text = {
            'text': 'Введите текст',
            'group': 'Группа, к которой будет относиться пост',
        }
        for field, value in dict_help_text.items():
            with self.subTest(field=field):
                self.assertEqual(
                    task._meta.get_field(field).help_text, value
                )
