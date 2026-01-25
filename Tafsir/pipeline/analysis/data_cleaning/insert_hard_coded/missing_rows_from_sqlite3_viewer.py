from bs4 import BeautifulSoup
import re

# Dein HTML hier einfügen
html_input = """
<div class="P" style="transform: translate(19080.1px, 26000px); width: 350px;"><div class="l" title="&lt;tafsir_section&gt;
&lt;tafsir_section_block&gt;
&lt;tafsir_chunk&gt;
&lt;opinions_of_scholars&gt;يخبر تعالى أنه أوحى إلى عبده ورسوله موسى ، عليه السلام ، في ذلك الموقف العظيم ، الذي فرق الله تعالى فيه بين الحق والباطل ، يأمره بأن يلقي ما في يمينه وهي عصاه&lt;/opinions_of_scholars&gt; ، &lt;quran_verse&gt;( فإذا هي تلقف )&lt;/quran_verse&gt; أي : &lt;opinions_of_scholars&gt;تأكل&lt;/opinions_of_scholars&gt; &lt;quran_verse&gt;( ما يأفكون )&lt;/quran_verse&gt; أي : &lt;opinions_of_scholars&gt;ما يلقونه ويوهمون أنه حق ، وهو باطل&lt;/opinions_of_scholars&gt; .
    &lt;/tafsir_chunk&gt;
&lt;tafsir_chunk&gt;
      قال &lt;opinions_of_scholars&gt;ابن عباس&lt;/opinions_of_scholars&gt; : &lt;opinions_of_scholars&gt;فجعلت لا تمر بشيء من حبالهم ولا من خشبهم إلا التقمته ، فعرفت السحرة أن هذا أمر من السماء ، وليس هذا بسحر ، فخروا سجدا وقالوا&lt;/opinions_of_scholars&gt; : &lt;quran_verse&gt;( آمنا برب العالمين رب موسى وهارون )&lt;/quran_verse&gt;
&lt;/tafsir_chunk&gt;
&lt;tafsir_chunk&gt;
      وقال &lt;opinions_of_scholars&gt;محمد بن إسحاق : جعلت تبتلع تلك الحبال والعصي واحدة ، واحدة حتى ما يرى بالوادي قليل ولا كثير مما ألقوا ، ثم أخذها موسى فإذا هي عصا في ي" tabindex="0" style="content-visibility: hidden; transform: translate(0px, 1664px); height: 26px;"><div class="Bl"><span>&lt;tafsir_section&gt;
&lt;tafsir_section_block&gt;
&lt;tafsir_chunk&gt;
&lt;opinions_of_scholars&gt;يخبر تعالى أنه أوحى إلى عبده ورسوله موسى ، عليه السلام ، في ذلك الموقف العظيم ، الذي فرق الله تعالى فيه بين الحق والباطل ، يأمره بأن يلقي ما في يمينه وهي عصاه&lt;/opinions_of_scholars&gt; ، &lt;quran_verse&gt;( فإذا هي تلقف )&lt;/quran_verse&gt; أي : &lt;opinions_of_scholars&gt;تأكل&lt;/opinions_of_scholars&gt; &lt;quran_verse&gt;( ما يأفكون )&lt;/quran_verse&gt; أي : &lt;opinions_of_scholars&gt;ما يلقونه ويوهمون أنه حق ، وهو باطل&lt;/opinions_of_scholars&gt; .
    &lt;/tafsir_chunk&gt;
&lt;tafsir_chunk&gt;
      قال &lt;opinions_of_scholars&gt;ابن عباس&lt;/opinions_of_scholars&gt; : &lt;opinions_of_scholars&gt;فجعلت لا تمر بشيء من حبالهم ولا من خشبهم إلا التقمته ، فعرفت السحرة أن هذا أمر من السماء ، وليس هذا بسحر ، فخروا سجدا وقالوا&lt;/opinions_of_scholars&gt; : &lt;quran_verse&gt;( آمنا برب العالمين رب موسى وهارون )&lt;/quran_verse&gt;
&lt;/tafsir_chunk&gt;
&lt;tafsir_chunk&gt;
      وقال &lt;opinions_of_scholars&gt;محمد بن إسحاق : جعلت تبتلع تلك الحبال والعصي واحدة ، واحدة حتى ما يرى بالوادي قليل ولا كثير مما ألقوا ، ثم أخذها موسى فإذا هي عصا في ي</span></div></div><div class="l Zo" title="&lt;tafsir_section&gt;
&lt;tafsir_section_block&gt;
&lt;tafsir_chunk&gt;
&lt;opinions_of_scholars&gt;يخبر تعالى عما توعد به فرعون ، لعنه الله ، السحرة لما آمنوا بموسى ، عليه السلام ، وما أظهره للناس من كيده ومكره في قوله&lt;/opinions_of_scholars&gt; : &lt;quran_verse&gt;( إن هذا لمكر مكرتموه في المدينة لتخرجوا منها أهلها )&lt;/quran_verse&gt; أي : &lt;opinions_of_scholars&gt;إن غلبه لكم في يومكم هذا إنما كان عن تشاور منكم ورضا منكم لذلك&lt;/opinions_of_scholars&gt; ، كقوله في الآية الأخرى : &lt;cross_references&gt;&lt;quran_verse&gt;( إنه لكبيركم الذي علمكم السحر )&lt;/quran_verse&gt; [ طه : 70 ]&lt;/cross_references&gt;
&lt;opinions_of_scholars&gt;وهو يعلم وكل من له لب أن هذا الذي قاله من أبطل الباطل ; فإن موسى ، عليه السلام ، بمجرد ما جاء من &quot; مدين &quot; دعا فرعون إلى الله ، وأظهر المعجزات الباهرة والحجج القاطعة على صدق ما جاء به ، فعند ذلك أرسل فرعون في مدائن ملكه ومعاملة سلطنته ، فجمع سحرة متفرقين من سائر الأقاليم ببلاد مصر ، ممن اختار هو والملأ من قومه ، وأحضرهم عنده ووعدهم بالعطاء الجزيل . وقد كانوا من أحرص الناس على ذلك ، وعلى الظهور في مقامهم ذلك والتقدم عند فرعون ، وموسى ، عليه السلام ،" tabindex="0" style="content-visibility: hidden; transform: translate(0px, 1690px); height: 26px;"><div class="Bl"><span>&lt;tafsir_section&gt;
&lt;tafsir_section_block&gt;
&lt;tafsir_chunk&gt;
&lt;opinions_of_scholars&gt;يخبر تعالى عما توعد به فرعون ، لعنه الله ، السحرة لما آمنوا بموسى ، عليه السلام ، وما أظهره للناس من كيده ومكره في قوله&lt;/opinions_of_scholars&gt; : &lt;quran_verse&gt;( إن هذا لمكر مكرتموه في المدينة لتخرجوا منها أهلها )&lt;/quran_verse&gt; أي : &lt;opinions_of_scholars&gt;إن غلبه لكم في يومكم هذا إنما كان عن تشاور منكم ورضا منكم لذلك&lt;/opinions_of_scholars&gt; ، كقوله في الآية الأخرى : &lt;cross_references&gt;&lt;quran_verse&gt;( إنه لكبيركم الذي علمكم السحر )&lt;/quran_verse&gt; [ طه : 70 ]&lt;/cross_references&gt;
&lt;opinions_of_scholars&gt;وهو يعلم وكل من له لب أن هذا الذي قاله من أبطل الباطل ; فإن موسى ، عليه السلام ، بمجرد ما جاء من " مدين " دعا فرعون إلى الله ، وأظهر المعجزات الباهرة والحجج القاطعة على صدق ما جاء به ، فعند ذلك أرسل فرعون في مدائن ملكه ومعاملة سلطنته ، فجمع سحرة متفرقين من سائر الأقاليم ببلاد مصر ، ممن اختار هو والملأ من قومه ، وأحضرهم عنده ووعدهم بالعطاء الجزيل . وقد كانوا من أحرص الناس على ذلك ، وعلى الظهور في مقامهم ذلك والتقدم عند فرعون ، وموسى ، عليه السلام ،</span></div></div><div class="l" title="XML&lt;tafsir_section&gt;
  &lt;tafsir_section_block&gt;
    &lt;tafsir_chunk&gt;
      ثم فسر هذا الوعيد بقوله : &lt;quran_verse&gt;( لأقطعن أيديكم وأرجلكم من خلاف )&lt;/quran_verse&gt; يعني : &lt;opinions_of_scholars&gt;يقطع يد الرجل اليمنى ورجله اليسرى أو بالعكس&lt;/opinions_of_scholars&gt; .
      &lt;quran_verse&gt;( لأصلبنكم أجمعين )&lt;/quran_verse&gt; وقال في الآية الأخرى : &lt;cross_references&gt;&lt;quran_verse&gt;( في جذوع النخل )&lt;/quran_verse&gt; [ طه : 71 ]&lt;/cross_references&gt; أي : &lt;opinions_of_scholars&gt;على الجذوع&lt;/opinions_of_scholars&gt; .
    &lt;/tafsir_chunk&gt;
    &lt;tafsir_chunk&gt;
      قال &lt;opinions_of_scholars&gt;ابن عباس : وكان أول من صلب ، وأول من قطع الأيدي والأرجل من خلاف ، فرعون&lt;/opinions_of_scholars&gt; .
    &lt;/tafsir_chunk&gt;
  &lt;/tafsir_section_block&gt;
&lt;/tafsir_section&gt;
" tabindex="0" style="content-visibility: hidden; transform: translate(0px, 1716px); height: 26px;"><div class="Bl"><span>XML&lt;tafsir_section&gt;
  &lt;tafsir_section_block&gt;
    &lt;tafsir_chunk&gt;
      ثم فسر هذا الوعيد بقوله : &lt;quran_verse&gt;( لأقطعن أيديكم وأرجلكم من خلاف )&lt;/quran_verse&gt; يعني : &lt;opinions_of_scholars&gt;يقطع يد الرجل اليمنى ورجله اليسرى أو بالعكس&lt;/opinions_of_scholars&gt; .
      &lt;quran_verse&gt;( لأصلبنكم أجمعين )&lt;/quran_verse&gt; وقال في الآية الأخرى : &lt;cross_references&gt;&lt;quran_verse&gt;( في جذوع النخل )&lt;/quran_verse&gt; [ طه : 71 ]&lt;/cross_references&gt; أي : &lt;opinions_of_scholars&gt;على الجذوع&lt;/opinions_of_scholars&gt; .
    &lt;/tafsir_chunk&gt;
    &lt;tafsir_chunk&gt;
      قال &lt;opinions_of_scholars&gt;ابن عباس : وكان أول من صلب ، وأول من قطع الأيدي والأرجل من خلاف ، فرعون&lt;/opinions_of_scholars&gt; .
    &lt;/tafsir_chunk&gt;
  &lt;/tafsir_section_block&gt;
&lt;/tafsir_section&gt;
</span></div></div><div class="l Zo" title="&lt;tafsir_section&gt;
&lt;tafsir_section_block&gt;
&lt;tafsir_chunk&gt;
      وقول السحرة : &lt;quran_verse&gt;( إنا إلى ربنا منقلبون )&lt;/quran_verse&gt; أي : &lt;opinions_of_scholars&gt;قد تحققنا أنا إليه راجعون ، وعذابه أشد من عذابك ، ونكاله ما تدعونا إليه ، وما أكرهتنا عليه من السحر ، أعظم من نكالك ، فلنصبرن اليوم على عذابك لنخلص من عذاب الله&lt;/opinions_of_scholars&gt;
&lt;/tafsir_chunk&gt;
&lt;/tafsir_section_block&gt;
&lt;/tafsir_section&gt;
" tabindex="0" style="content-visibility: hidden; transform: translate(0px, 1742px); height: 26px;"><div class="Bl"><span>&lt;tafsir_section&gt;
&lt;tafsir_section_block&gt;
&lt;tafsir_chunk&gt;
      وقول السحرة : &lt;quran_verse&gt;( إنا إلى ربنا منقلبون )&lt;/quran_verse&gt; أي : &lt;opinions_of_scholars&gt;قد تحققنا أنا إليه راجعون ، وعذابه أشد من عذابك ، ونكاله ما تدعونا إليه ، وما أكرهتنا عليه من السحر ، أعظم من نكالك ، فلنصبرن اليوم على عذابك لنخلص من عذاب الله&lt;/opinions_of_scholars&gt;
&lt;/tafsir_chunk&gt;
&lt;/tafsir_section_block&gt;
&lt;/tafsir_section&gt;
</span></div></div><div class="l" title="&lt;tafsir_section&gt;
&lt;tafsir_section_block&gt;
&lt;tafsir_chunk&gt;
      لما قالوا : &lt;quran_verse&gt;( ربنا أفرغ علينا صبرا )&lt;/quran_verse&gt; أي : &lt;opinions_of_scholars&gt;عمنا بالصبر على دينك ، والثبات عليه&lt;/opinions_of_scholars&gt; ، &lt;quran_verse&gt;( وتوفنا مسلمين )&lt;/quran_verse&gt; أي : &lt;opinions_of_scholars&gt;متابعين لنبيك موسى ، عليه السلام&lt;/opinions_of_scholars&gt; .
    &lt;/tafsir_chunk&gt;
&lt;tafsir_chunk&gt;
      وقالوا لفرعون : &lt;cross_references&gt;&lt;quran_verse&gt;( فاقض ما أنت قاض إنما تقضي هذه الحياة الدنيا إنا آمنا بربنا ليغفر لنا خطايانا وما أكرهتنا عليه من السحر والله خير وأبقى إنه من يأت ربه مجرما فإن له جهنم لا يموت فيها ولا يحيا ومن يأته مؤمنا قد عمل الصالحات فأولئك لهم الدرجات العلا )&lt;/quran_verse&gt; [ طه : 72 - 75 ]&lt;/cross_references&gt;
&lt;/tafsir_chunk&gt;
&lt;tafsir_chunk&gt;
&lt;opinions_of_scholars&gt;فكانوا في أول النهار سحرة ، فصاروا في آخره شهداء بررة&lt;/opinions_of_scholars&gt; . قال &lt;opinions_of_scholars&gt;ابن عباس ، وعبيد بن عمير ، وقتادة ، وابن جريج : كانوا في أول النهار سحرة ، وفي آخره شهداء&lt;/opinions_of_scholars&gt; .
    &lt;/tafsir_chunk&gt;
&lt;/tafsir_section" tabindex="0" style="content-visibility: hidden; transform: translate(0px, 1768px); height: 26px;"><div class="Bl"><span>&lt;tafsir_section&gt;
&lt;tafsir_section_block&gt;
&lt;tafsir_chunk&gt;
      لما قالوا : &lt;quran_verse&gt;( ربنا أفرغ علينا صبرا )&lt;/quran_verse&gt; أي : &lt;opinions_of_scholars&gt;عمنا بالصبر على دينك ، والثبات عليه&lt;/opinions_of_scholars&gt; ، &lt;quran_verse&gt;( وتوفنا مسلمين )&lt;/quran_verse&gt; أي : &lt;opinions_of_scholars&gt;متابعين لنبيك موسى ، عليه السلام&lt;/opinions_of_scholars&gt; .
    &lt;/tafsir_chunk&gt;
&lt;tafsir_chunk&gt;
      وقالوا لفرعون : &lt;cross_references&gt;&lt;quran_verse&gt;( فاقض ما أنت قاض إنما تقضي هذه الحياة الدنيا إنا آمنا بربنا ليغفر لنا خطايانا وما أكرهتنا عليه من السحر والله خير وأبقى إنه من يأت ربه مجرما فإن له جهنم لا يموت فيها ولا يحيا ومن يأته مؤمنا قد عمل الصالحات فأولئك لهم الدرجات العلا )&lt;/quran_verse&gt; [ طه : 72 - 75 ]&lt;/cross_references&gt;
&lt;/tafsir_chunk&gt;
&lt;tafsir_chunk&gt;
&lt;opinions_of_scholars&gt;فكانوا في أول النهار سحرة ، فصاروا في آخره شهداء بررة&lt;/opinions_of_scholars&gt; . قال &lt;opinions_of_scholars&gt;ابن عباس ، وعبيد بن عمير ، وقتادة ، وابن جريج : كانوا في أول النهار سحرة ، وفي آخره شهداء&lt;/opinions_of_scholars&gt; .
    &lt;/tafsir_chunk&gt;
&lt;/tafsir_section</span></div></div><div class="l Zo" title="&lt;tafsir_section&gt;
&lt;tafsir_section_block&gt;
&lt;tafsir_chunk&gt;
&lt;opinions_of_scholars&gt;يخبر تعالى عما تمالأ عليه فرعون وملؤه ، وما أظهروه لموسى ، عليه السلام ، وقومه من الأذى والبغضة&lt;/opinions_of_scholars&gt; : &lt;quran_verse&gt;( وقال الملأ من قوم فرعون )&lt;/quran_verse&gt; أي : &lt;opinions_of_scholars&gt;لفرعون&lt;/opinions_of_scholars&gt; &lt;quran_verse&gt;( أتذر موسى وقومه )&lt;/quran_verse&gt; أي : &lt;opinions_of_scholars&gt;أتدعهم ليفسدوا في الأرض ، أي : يفسدوا أهل رعيتك ويدعوهم إلى عبادة ربهم دونك ، يالله للعجب ! صار هؤلاء يشفقون من إفساد موسى وقومه ! ألا إن فرعون وقومه هم المفسدون ، ولكن لا يشعرون&lt;/opinions_of_scholars&gt; ; ولهذا قالوا : &lt;quran_verse&gt;( ويذرك وآلهتك )&lt;/quran_verse&gt;
&lt;/tafsir_chunk&gt;
&lt;tafsir_chunk&gt;
&lt;opinions_of_scholars&gt;قال بعضهم : &quot; الواو &quot; هنا حالية ، أي : أتذره وقومه يفسدون وقد ترك عبادتك ؟&lt;/opinions_of_scholars&gt; وقرأ ذلك &lt;opinions_of_scholars&gt;أبي بن كعب&lt;/opinions_of_scholars&gt; : &lt;opinions_of_scholars&gt;&quot; وقد تركوك أن يعبدوك وآلهتك &quot;&lt;/opinions_of_scholars&gt; ، &lt;source&gt;حكاه ابن جرير&lt;/source&gt; .
      وقال &lt;opinions_of_scholars&gt;آخرون : هي عاطفة" tabindex="0" style="content-visibility: hidden; transform: translate(0px, 1794px); height: 26px;"><div class="Bl"><span>&lt;tafsir_section&gt;
&lt;tafsir_section_block&gt;
&lt;tafsir_chunk&gt;
&lt;opinions_of_scholars&gt;يخبر تعالى عما تمالأ عليه فرعون وملؤه ، وما أظهروه لموسى ، عليه السلام ، وقومه من الأذى والبغضة&lt;/opinions_of_scholars&gt; : &lt;quran_verse&gt;( وقال الملأ من قوم فرعون )&lt;/quran_verse&gt; أي : &lt;opinions_of_scholars&gt;لفرعون&lt;/opinions_of_scholars&gt; &lt;quran_verse&gt;( أتذر موسى وقومه )&lt;/quran_verse&gt; أي : &lt;opinions_of_scholars&gt;أتدعهم ليفسدوا في الأرض ، أي : يفسدوا أهل رعيتك ويدعوهم إلى عبادة ربهم دونك ، يالله للعجب ! صار هؤلاء يشفقون من إفساد موسى وقومه ! ألا إن فرعون وقومه هم المفسدون ، ولكن لا يشعرون&lt;/opinions_of_scholars&gt; ; ولهذا قالوا : &lt;quran_verse&gt;( ويذرك وآلهتك )&lt;/quran_verse&gt;
&lt;/tafsir_chunk&gt;
&lt;tafsir_chunk&gt;
&lt;opinions_of_scholars&gt;قال بعضهم : " الواو " هنا حالية ، أي : أتذره وقومه يفسدون وقد ترك عبادتك ؟&lt;/opinions_of_scholars&gt; وقرأ ذلك &lt;opinions_of_scholars&gt;أبي بن كعب&lt;/opinions_of_scholars&gt; : &lt;opinions_of_scholars&gt;" وقد تركوك أن يعبدوك وآلهتك "&lt;/opinions_of_scholars&gt; ، &lt;source&gt;حكاه ابن جرير&lt;/source&gt; .
      وقال &lt;opinions_of_scholars&gt;آخرون : هي عاطفة</span></div></div><div class="l" title="XML&lt;tafsir_section&gt;
  &lt;tafsir_section_block&gt;
    &lt;tafsir_chunk&gt;
      &lt;opinions_of_scholars&gt;ولما صمم فرعون على ما ذكره من المساءة لبني إسرائيل ،&lt;/opinions_of_scholars&gt; &lt;quran_verse&gt;( قال موسى لقومه استعينوا بالله واصبروا )&lt;/quran_verse&gt; &lt;opinions_of_scholars&gt;ووعدهم بالعاقبة ، وأن الدار ستصير لهم في قوله :&lt;/opinions_of_scholars&gt; &lt;quran_verse&gt;( إن الأرض لله يورثها من يشاء من عباده والعاقبة للمتقين )&lt;/quran_verse&gt;
    &lt;/tafsir_chunk&gt;
  &lt;/tafsir_section_block&gt;
&lt;/tafsir_section&gt;
" tabindex="0" style="content-visibility: hidden; transform: translate(0px, 1820px); height: 26px;"><div class="Bl"><span>XML&lt;tafsir_section&gt;
  &lt;tafsir_section_block&gt;
    &lt;tafsir_chunk&gt;
      &lt;opinions_of_scholars&gt;ولما صمم فرعون على ما ذكره من المساءة لبني إسرائيل ،&lt;/opinions_of_scholars&gt; &lt;quran_verse&gt;( قال موسى لقومه استعينوا بالله واصبروا )&lt;/quran_verse&gt; &lt;opinions_of_scholars&gt;ووعدهم بالعاقبة ، وأن الدار ستصير لهم في قوله :&lt;/opinions_of_scholars&gt; &lt;quran_verse&gt;( إن الأرض لله يورثها من يشاء من عباده والعاقبة للمتقين )&lt;/quran_verse&gt;
    &lt;/tafsir_chunk&gt;
  &lt;/tafsir_section_block&gt;
&lt;/tafsir_section&gt;
</span></div></div><div class="l Zo" title="&lt;tafsir_section&gt;
&lt;tafsir_section_block&gt;
&lt;tafsir_chunk&gt;
&lt;quran_verse&gt;&quot;قالوا أوذينا من قبل أن تأتينا ومن بعد ما جئتنا&quot;&lt;/quran_verse&gt; أي : &lt;opinions_of_scholars&gt;قد جرى علينا مثل ما رأيت من الهوان والإذلال من قبل ما جئت يا موسى ، ومن بعد ذلك&lt;/opinions_of_scholars&gt; .
    &lt;/tafsir_chunk&gt;
&lt;tafsir_chunk&gt;
      فقال منبها لهم على حالهم الحاضرة وما يصيرون إليه في ثاني الحال : &lt;quran_verse&gt;( عسى ربكم أن يهلك عدوكم [ ويستخلفكم في الأرض فينظر كيف تعملون ] )&lt;/quran_verse&gt; &lt;opinions_of_scholars&gt;وهذا تحضيض لهم على العزم على الشكر ، عند حلول النعم وزوال النقم&lt;/opinions_of_scholars&gt; .
    &lt;/tafsir_chunk&gt;
&lt;/tafsir_section_block&gt;
&lt;/tafsir_section&gt;
" tabindex="0" style="content-visibility: hidden; transform: translate(0px, 1846px); height: 26px;"><div class="Bl"><span>&lt;tafsir_section&gt;
&lt;tafsir_section_block&gt;
&lt;tafsir_chunk&gt;
&lt;quran_verse&gt;"قالوا أوذينا من قبل أن تأتينا ومن بعد ما جئتنا"&lt;/quran_verse&gt; أي : &lt;opinions_of_scholars&gt;قد جرى علينا مثل ما رأيت من الهوان والإذلال من قبل ما جئت يا موسى ، ومن بعد ذلك&lt;/opinions_of_scholars&gt; .
    &lt;/tafsir_chunk&gt;
&lt;tafsir_chunk&gt;
      فقال منبها لهم على حالهم الحاضرة وما يصيرون إليه في ثاني الحال : &lt;quran_verse&gt;( عسى ربكم أن يهلك عدوكم [ ويستخلفكم في الأرض فينظر كيف تعملون ] )&lt;/quran_verse&gt; &lt;opinions_of_scholars&gt;وهذا تحضيض لهم على العزم على الشكر ، عند حلول النعم وزوال النقم&lt;/opinions_of_scholars&gt; .
    &lt;/tafsir_chunk&gt;
&lt;/tafsir_section_block&gt;
&lt;/tafsir_section&gt;
</span></div></div><div class="l" title="&lt;tafsir_section&gt;
&lt;tafsir_section_block&gt;
&lt;tafsir_chunk&gt;
      يقول تعالى : &lt;quran_verse&gt;( ولقد أخذنا آل فرعون )&lt;/quran_verse&gt; أي : &lt;opinions_of_scholars&gt;اختبرناهم وامتحناهم وابتليناهم&lt;/opinions_of_scholars&gt; &lt;quran_verse&gt;( بالسنين )&lt;/quran_verse&gt; &lt;opinions_of_scholars&gt;وهي سني الجوع بسبب قلة الزروع&lt;/opinions_of_scholars&gt; &lt;quran_verse&gt;( ونقص من الثمرات )&lt;/quran_verse&gt;
&lt;/tafsir_chunk&gt;
&lt;tafsir_chunk&gt;
      قال &lt;opinions_of_scholars&gt;مجاهد : وهو دون ذلك&lt;/opinions_of_scholars&gt; .
      وقال &lt;opinions_of_scholars&gt;أبو إسحاق ، عن رجاء بن حيوة : كانت النخلة لا تحمل إلا ثمرة واحدة&lt;/opinions_of_scholars&gt; . &lt;quran_verse&gt;( لعلهم يذكرون )&lt;/quran_verse&gt;
&lt;/tafsir_chunk&gt;
&lt;/tafsir_section_block&gt;
&lt;/tafsir_section&gt;
" tabindex="0" style="content-visibility: hidden; transform: translate(0px, 1872px); height: 26px;"><div class="Bl"><span>&lt;tafsir_section&gt;
&lt;tafsir_section_block&gt;
&lt;tafsir_chunk&gt;
      يقول تعالى : &lt;quran_verse&gt;( ولقد أخذنا آل فرعون )&lt;/quran_verse&gt; أي : &lt;opinions_of_scholars&gt;اختبرناهم وامتحناهم وابتليناهم&lt;/opinions_of_scholars&gt; &lt;quran_verse&gt;( بالسنين )&lt;/quran_verse&gt; &lt;opinions_of_scholars&gt;وهي سني الجوع بسبب قلة الزروع&lt;/opinions_of_scholars&gt; &lt;quran_verse&gt;( ونقص من الثمرات )&lt;/quran_verse&gt;
&lt;/tafsir_chunk&gt;
&lt;tafsir_chunk&gt;
      قال &lt;opinions_of_scholars&gt;مجاهد : وهو دون ذلك&lt;/opinions_of_scholars&gt; .
      وقال &lt;opinions_of_scholars&gt;أبو إسحاق ، عن رجاء بن حيوة : كانت النخلة لا تحمل إلا ثمرة واحدة&lt;/opinions_of_scholars&gt; . &lt;quran_verse&gt;( لعلهم يذكرون )&lt;/quran_verse&gt;
&lt;/tafsir_chunk&gt;
&lt;/tafsir_section_block&gt;
&lt;/tafsir_section&gt;
</span></div></div><div class="l Zo" title="&lt;tafsir_section&gt;
&lt;tafsir_section_block&gt;
&lt;tafsir_chunk&gt;
&lt;quran_verse&gt;&quot;فإذا جاءتهم الحسنة&quot;&lt;/quran_verse&gt; أي : &lt;opinions_of_scholars&gt;من الخصب والرزق&lt;/opinions_of_scholars&gt; &lt;quran_verse&gt;( قالوا لنا هذه )&lt;/quran_verse&gt; أي : &lt;opinions_of_scholars&gt;هذا لنا بما نستحقه&lt;/opinions_of_scholars&gt; ، &lt;quran_verse&gt;( وإن تصبهم سيئة )&lt;/quran_verse&gt; أي : &lt;opinions_of_scholars&gt;جدب وقحط&lt;/opinions_of_scholars&gt; &lt;quran_verse&gt;( يطيروا بموسى ومن معه )&lt;/quran_verse&gt; أي : &lt;opinions_of_scholars&gt;هذا بسببهم وما جاءوا به&lt;/opinions_of_scholars&gt; .
    &lt;/tafsir_chunk&gt;
&lt;tafsir_chunk&gt;
&lt;quran_verse&gt;( ألا إنما طائرهم عند الله )&lt;/quran_verse&gt; قال &lt;opinions_of_scholars&gt;علي بن أبي طلحة ، عن ابن عباس&lt;/opinions_of_scholars&gt; : &lt;quran_verse&gt;( ألا إنما طائرهم عند الله )&lt;/quran_verse&gt; يقول : &lt;opinions_of_scholars&gt;مصائبهم عند الله&lt;/opinions_of_scholars&gt; ، قال الله : &lt;quran_verse&gt;( ولكن أكثرهم لا يعلمون )&lt;/quran_verse&gt;
&lt;/tafsir_chunk&gt;
&lt;tafsir_chunk&gt;
      وقال &lt;opinions_of_scholars&gt;ابن جريج ، عن ابن عباس&lt;/opinions_of_scholars&gt; قال : &lt;quran_verse&gt;( ألا إنما طائ" tabindex="0" style="content-visibility: hidden; transform: translate(0px, 1898px); height: 26px;"><div class="Bl"><span>&lt;tafsir_section&gt;
&lt;tafsir_section_block&gt;
&lt;tafsir_chunk&gt;
&lt;quran_verse&gt;"فإذا جاءتهم الحسنة"&lt;/quran_verse&gt; أي : &lt;opinions_of_scholars&gt;من الخصب والرزق&lt;/opinions_of_scholars&gt; &lt;quran_verse&gt;( قالوا لنا هذه )&lt;/quran_verse&gt; أي : &lt;opinions_of_scholars&gt;هذا لنا بما نستحقه&lt;/opinions_of_scholars&gt; ، &lt;quran_verse&gt;( وإن تصبهم سيئة )&lt;/quran_verse&gt; أي : &lt;opinions_of_scholars&gt;جدب وقحط&lt;/opinions_of_scholars&gt; &lt;quran_verse&gt;( يطيروا بموسى ومن معه )&lt;/quran_verse&gt; أي : &lt;opinions_of_scholars&gt;هذا بسببهم وما جاءوا به&lt;/opinions_of_scholars&gt; .
    &lt;/tafsir_chunk&gt;
&lt;tafsir_chunk&gt;
&lt;quran_verse&gt;( ألا إنما طائرهم عند الله )&lt;/quran_verse&gt; قال &lt;opinions_of_scholars&gt;علي بن أبي طلحة ، عن ابن عباس&lt;/opinions_of_scholars&gt; : &lt;quran_verse&gt;( ألا إنما طائرهم عند الله )&lt;/quran_verse&gt; يقول : &lt;opinions_of_scholars&gt;مصائبهم عند الله&lt;/opinions_of_scholars&gt; ، قال الله : &lt;quran_verse&gt;( ولكن أكثرهم لا يعلمون )&lt;/quran_verse&gt;
&lt;/tafsir_chunk&gt;
&lt;tafsir_chunk&gt;
      وقال &lt;opinions_of_scholars&gt;ابن جريج ، عن ابن عباس&lt;/opinions_of_scholars&gt; قال : &lt;quran_verse&gt;( ألا إنما طائ</span></div></div><div class="l" title="&lt;tafsir_section&gt;
&lt;tafsir_section_block&gt;
&lt;tafsir_chunk&gt;
&lt;opinions_of_scholars&gt;هذا إخبار من الله عز وجل عن تمرد قوم فرعون وعتوهم وعنادهم للحق وإصرارهم على الباطل في قولهم&lt;/opinions_of_scholars&gt; &lt;quran_verse&gt;&quot;مهما تأتنا به من آية لتسحرنا بها فما نحن لك بمؤمنين&quot;&lt;/quran_verse&gt; &lt;opinions_of_scholars&gt;يقولون أي آية جئتنا بها ودلالة وحجة أقمتها رددناها فلا نقبلها منك ولا نؤمن بك ولا بما جئت به&lt;/opinions_of_scholars&gt; .
    &lt;/tafsir_chunk&gt;
&lt;/tafsir_section_block&gt;
&lt;/tafsir_section&gt;
" tabindex="0" style="content-visibility: hidden; transform: translate(0px, 1924px); height: 26px;"><div class="Bl"><span>&lt;tafsir_section&gt;
&lt;tafsir_section_block&gt;
&lt;tafsir_chunk&gt;
&lt;opinions_of_scholars&gt;هذا إخبار من الله عز وجل عن تمرد قوم فرعون وعتوهم وعنادهم للحق وإصرارهم على الباطل في قولهم&lt;/opinions_of_scholars&gt; &lt;quran_verse&gt;"مهما تأتنا به من آية لتسحرنا بها فما نحن لك بمؤمنين"&lt;/quran_verse&gt; &lt;opinions_of_scholars&gt;يقولون أي آية جئتنا بها ودلالة وحجة أقمتها رددناها فلا نقبلها منك ولا نؤمن بك ولا بما جئت به&lt;/opinions_of_scholars&gt; .
    &lt;/tafsir_chunk&gt;
&lt;/tafsir_section_block&gt;
&lt;/tafsir_section&gt;
</span></div></div><div class="l Zo" title="&lt;tafsir_section&gt;
&lt;tafsir_section_block&gt;
&lt;tafsir_chunk&gt;
&lt;opinions_of_scholars&gt;فأرسل الطوفان وهو الماء ففاض على وجه الأرض ثم ركد لا يقدرون على أن يحرثوا ولا أن يعملوا شيئا حتى جهدوا جوعا فلما بلغهم ذلك&lt;/opinions_of_scholars&gt; &lt;quran_verse&gt;&quot;قالوا يا موسى ادع لنا ربك بما عهد عندك لئن كشفت عنا الرجز لنؤمنن لك ولنرسلن معك بني إسرائيل&quot;&lt;/quran_verse&gt; &lt;opinions_of_scholars&gt;فدعا موسى ربه&lt;/opinions_of_scholars&gt; .
    &lt;/tafsir_chunk&gt;
&lt;/tafsir_section_block&gt;
&lt;/tafsir_section&gt;
" tabindex="0" style="content-visibility: hidden; transform: translate(0px, 1950px); height: 26px;"><div class="Bl"><span>&lt;tafsir_section&gt;
&lt;tafsir_section_block&gt;
&lt;tafsir_chunk&gt;
&lt;opinions_of_scholars&gt;فأرسل الطوفان وهو الماء ففاض على وجه الأرض ثم ركد لا يقدرون على أن يحرثوا ولا أن يعملوا شيئا حتى جهدوا جوعا فلما بلغهم ذلك&lt;/opinions_of_scholars&gt; &lt;quran_verse&gt;"قالوا يا موسى ادع لنا ربك بما عهد عندك لئن كشفت عنا الرجز لنؤمنن لك ولنرسلن معك بني إسرائيل"&lt;/quran_verse&gt; &lt;opinions_of_scholars&gt;فدعا موسى ربه&lt;/opinions_of_scholars&gt; .
    &lt;/tafsir_chunk&gt;
&lt;/tafsir_section_block&gt;
&lt;/tafsir_section&gt;
</span></div></div><div class="l" title="&lt;tafsir_section&gt;
&lt;tafsir_section_block&gt;
&lt;tafsir_chunk&gt;
&lt;opinions_of_scholars&gt;كشف عنهم فلم يفوا له بشيء مما قالوا فأرسل الله عليهم الجراد فأكل الشجر فيما بلغني حتى إن كان ليأكل مسامير الأبواب من الحديد حتى تقع دورهم ومساكنهم فقالوا مثل ما قالوا فدعا ربه فكشف عنهم فلم يفوا له بشيء مما قالوا فأرسل الله عليهم القمل فذكر لي أن موسى عليه السلام أمر أن يمشي إلى كثيب حتى يضربه بعصاه فمشى إلى كثيب أهيل عظيم فضربه بها فانثال عليهم قملا حتى غلب على البيوت والأطعمة ومنعهم النوم والقرار فلما جهدهم قالوا له مثل ما قالوا له فدعا ربه فكشف عنهم فلم يفوا له بشيء مما قالوا فأرسل الله عليهم الضفادع فملأت البيوت والأطعمة والآنية فلا يكشف أحد ثوبا ولا طعاما إلا وجد فيه الضفادع قد غلبت عليه فلما جهدهم ذلك قالوا له مثل ما قالوا فسأل ربه فكشف عنهم فلم يفوا له بشيء مما قالوا فأرسل الله عليهم الدم فصارت مياه آل فرعون دما لا يستقون من بئر ولا نهر ولا يغترفون من إناء إلا عاد دما عبيطا&lt;/opinions_of_scholars&gt; .
    &lt;/tafsir_chunk&gt;
&lt;tafsir_chunk&gt;
      وقال &lt;source&gt;ابن أبي حاتم : حدثنا أحمد بن منصور المروزي أنا النضر أنا إسرائيل أنا جابر بن" tabindex="0" style="content-visibility: hidden; transform: translate(0px, 1976px); height: 26px;"><div class="Bl"><span>&lt;tafsir_section&gt;
&lt;tafsir_section_block&gt;
&lt;tafsir_chunk&gt;
&lt;opinions_of_scholars&gt;كشف عنهم فلم يفوا له بشيء مما قالوا فأرسل الله عليهم الجراد فأكل الشجر فيما بلغني حتى إن كان ليأكل مسامير الأبواب من الحديد حتى تقع دورهم ومساكنهم فقالوا مثل ما قالوا فدعا ربه فكشف عنهم فلم يفوا له بشيء مما قالوا فأرسل الله عليهم القمل فذكر لي أن موسى عليه السلام أمر أن يمشي إلى كثيب حتى يضربه بعصاه فمشى إلى كثيب أهيل عظيم فضربه بها فانثال عليهم قملا حتى غلب على البيوت والأطعمة ومنعهم النوم والقرار فلما جهدهم قالوا له مثل ما قالوا له فدعا ربه فكشف عنهم فلم يفوا له بشيء مما قالوا فأرسل الله عليهم الضفادع فملأت البيوت والأطعمة والآنية فلا يكشف أحد ثوبا ولا طعاما إلا وجد فيه الضفادع قد غلبت عليه فلما جهدهم ذلك قالوا له مثل ما قالوا فسأل ربه فكشف عنهم فلم يفوا له بشيء مما قالوا فأرسل الله عليهم الدم فصارت مياه آل فرعون دما لا يستقون من بئر ولا نهر ولا يغترفون من إناء إلا عاد دما عبيطا&lt;/opinions_of_scholars&gt; .
    &lt;/tafsir_chunk&gt;
&lt;tafsir_chunk&gt;
      وقال &lt;source&gt;ابن أبي حاتم : حدثنا أحمد بن منصور المروزي أنا النضر أنا إسرائيل أنا جابر بن</span></div></div><div class="l Zo" title="&lt;tafsir_section&gt;
&lt;tafsir_section_block&gt;
&lt;tafsir_chunk&gt;
&lt;opinions_of_scholars&gt;يخبر تعالى أنهم لما عتوا وتمردوا ، مع ابتلائه إياهم بالآيات المتواترة واحدة بعد واحدة ، [ أنه ] انتقم منهم بإغراقه إياهم في اليم ، وهو البحر الذي فرقه لموسى ، فجاوزه وبنو إسرائيل معه ، ثم ورده فرعون وجنوده على أثرهم ، فلما استكملوا فيه ارتطم عليهم ، فغرقوا عن آخرهم ، وذلك بسبب تكذيبهم بآيات الله وتغافلهم عنها&lt;/opinions_of_scholars&gt; .
    &lt;/tafsir_chunk&gt;
&lt;/tafsir_section_block&gt;
&lt;/tafsir_section&gt;
" tabindex="0" style="content-visibility: hidden; transform: translate(0px, 2002px); height: 26px;"><div class="Bl"><span>&lt;tafsir_section&gt;
&lt;tafsir_section_block&gt;
&lt;tafsir_chunk&gt;
&lt;opinions_of_scholars&gt;يخبر تعالى أنهم لما عتوا وتمردوا ، مع ابتلائه إياهم بالآيات المتواترة واحدة بعد واحدة ، [ أنه ] انتقم منهم بإغراقه إياهم في اليم ، وهو البحر الذي فرقه لموسى ، فجاوزه وبنو إسرائيل معه ، ثم ورده فرعون وجنوده على أثرهم ، فلما استكملوا فيه ارتطم عليهم ، فغرقوا عن آخرهم ، وذلك بسبب تكذيبهم بآيات الله وتغافلهم عنها&lt;/opinions_of_scholars&gt; .
    &lt;/tafsir_chunk&gt;
&lt;/tafsir_section_block&gt;
&lt;/tafsir_section&gt;
</span></div></div><div class="l" title="&lt;tafsir_section&gt;
&lt;tafsir_section_block&gt;
&lt;tafsir_chunk&gt;
&lt;opinions_of_scholars&gt;وأخبر تعالى أنه أورث القوم الذين كانوا يستضعفون - وهم بنو إسرائيل - مشارق الأرض ومغاربها&lt;/opinions_of_scholars&gt; كما قال تعالى : &lt;cross_references&gt;&lt;quran_verse&gt;( ونريد أن نمن على الذين استضعفوا في الأرض ونجعلهم أئمة ونجعلهم الوارثين ونمكن لهم في الأرض ونري فرعون وهامان وجنودهما منهم ما كانوا يحذرون )&lt;/quran_verse&gt; [ القصص : 5 ، 6 ]&lt;/cross_references&gt; وقال تعالى : &lt;cross_references&gt;&lt;quran_verse&gt;( كم تركوا من جنات وعيون وزروع ومقام كريم ونعمة كانوا فيها فاكهين كذلك وأورثناها قوما آخرين )&lt;/quran_verse&gt; [ الدخان : 25 - 28 ]&lt;/cross_references&gt;
&lt;/tafsir_chunk&gt;
&lt;tafsir_chunk&gt;
      وعن &lt;opinions_of_scholars&gt;الحسن البصري وقتادة&lt;/opinions_of_scholars&gt; ، في قوله : &lt;quran_verse&gt;( مشارق الأرض ومغاربها التي باركنا فيها )&lt;/quran_verse&gt; يعني : &lt;opinions_of_scholars&gt;الشام&lt;/opinions_of_scholars&gt; .
    &lt;/tafsir_chunk&gt;
&lt;tafsir_chunk&gt;
      وقوله : &lt;quran_verse&gt;( وتمت كلمة ربك الحسنى على بني إسرائيل بما صبروا )&lt;/quran_verse&gt; قال &lt;opinions_of_scholars&gt;مجا" tabindex="0" style="content-visibility: hidden; transform: translate(0px, 2028px); height: 26px;"><div class="Bl"><span>&lt;tafsir_section&gt;
&lt;tafsir_section_block&gt;
&lt;tafsir_chunk&gt;
&lt;opinions_of_scholars&gt;وأخبر تعالى أنه أورث القوم الذين كانوا يستضعفون - وهم بنو إسرائيل - مشارق الأرض ومغاربها&lt;/opinions_of_scholars&gt; كما قال تعالى : &lt;cross_references&gt;&lt;quran_verse&gt;( ونريد أن نمن على الذين استضعفوا في الأرض ونجعلهم أئمة ونجعلهم الوارثين ونمكن لهم في الأرض ونري فرعون وهامان وجنودهما منهم ما كانوا يحذرون )&lt;/quran_verse&gt; [ القصص : 5 ، 6 ]&lt;/cross_references&gt; وقال تعالى : &lt;cross_references&gt;&lt;quran_verse&gt;( كم تركوا من جنات وعيون وزروع ومقام كريم ونعمة كانوا فيها فاكهين كذلك وأورثناها قوما آخرين )&lt;/quran_verse&gt; [ الدخان : 25 - 28 ]&lt;/cross_references&gt;
&lt;/tafsir_chunk&gt;
&lt;tafsir_chunk&gt;
      وعن &lt;opinions_of_scholars&gt;الحسن البصري وقتادة&lt;/opinions_of_scholars&gt; ، في قوله : &lt;quran_verse&gt;( مشارق الأرض ومغاربها التي باركنا فيها )&lt;/quran_verse&gt; يعني : &lt;opinions_of_scholars&gt;الشام&lt;/opinions_of_scholars&gt; .
    &lt;/tafsir_chunk&gt;
&lt;tafsir_chunk&gt;
      وقوله : &lt;quran_verse&gt;( وتمت كلمة ربك الحسنى على بني إسرائيل بما صبروا )&lt;/quran_verse&gt; قال &lt;opinions_of_scholars&gt;مجا</span></div></div><div class="l Zo" title="&lt;tafsir_section&gt;
&lt;tafsir_section_block&gt;
&lt;tafsir_chunk&gt;
&lt;opinions_of_scholars&gt;يخبر تعالى عما قاله جهلة بني إسرائيل لموسى ، عليه السلام ، حين جاوزوا البحر ، وقد رأوا من آيات الله وعظيم سلطانه ما رأوا ،&lt;/opinions_of_scholars&gt; &lt;quran_verse&gt;( فأتوا )&lt;/quran_verse&gt; أي : &lt;opinions_of_scholars&gt;فمروا&lt;/opinions_of_scholars&gt; &lt;quran_verse&gt;( على قوم يعكفون على أصنام لهم )&lt;/quran_verse&gt;
&lt;/tafsir_chunk&gt;
&lt;tafsir_chunk&gt;
      قال &lt;opinions_of_scholars&gt;بعض المفسرين : كانوا من الكنعانيين . وقيل : كانوا من لخم&lt;/opinions_of_scholars&gt; .
      وقال &lt;opinions_of_scholars&gt;ابن جريج : وكانوا يعبدون أصناما على صور البقر ، فلهذا أثار ذلك شبهة لهم في عبادتهم العجل بعد ذلك&lt;/opinions_of_scholars&gt; ، فقالوا : &lt;quran_verse&gt;( يا موسى اجعل لنا إلها كما لهم آلهة قال إنكم قوم تجهلون )&lt;/quran_verse&gt; أي : &lt;opinions_of_scholars&gt;تجهلون عظمة الله وجلاله ، وما يجب أن ينزه عنه من الشريك والمثيل&lt;/opinions_of_scholars&gt; .
    &lt;/tafsir_chunk&gt;
&lt;/tafsir_section_block&gt;
&lt;/tafsir_section&gt;
" tabindex="0" style="content-visibility: hidden; transform: translate(0px, 2054px); height: 26px;"><div class="Bl"><span>&lt;tafsir_section&gt;
&lt;tafsir_section_block&gt;
&lt;tafsir_chunk&gt;
&lt;opinions_of_scholars&gt;يخبر تعالى عما قاله جهلة بني إسرائيل لموسى ، عليه السلام ، حين جاوزوا البحر ، وقد رأوا من آيات الله وعظيم سلطانه ما رأوا ،&lt;/opinions_of_scholars&gt; &lt;quran_verse&gt;( فأتوا )&lt;/quran_verse&gt; أي : &lt;opinions_of_scholars&gt;فمروا&lt;/opinions_of_scholars&gt; &lt;quran_verse&gt;( على قوم يعكفون على أصنام لهم )&lt;/quran_verse&gt;
&lt;/tafsir_chunk&gt;
&lt;tafsir_chunk&gt;
      قال &lt;opinions_of_scholars&gt;بعض المفسرين : كانوا من الكنعانيين . وقيل : كانوا من لخم&lt;/opinions_of_scholars&gt; .
      وقال &lt;opinions_of_scholars&gt;ابن جريج : وكانوا يعبدون أصناما على صور البقر ، فلهذا أثار ذلك شبهة لهم في عبادتهم العجل بعد ذلك&lt;/opinions_of_scholars&gt; ، فقالوا : &lt;quran_verse&gt;( يا موسى اجعل لنا إلها كما لهم آلهة قال إنكم قوم تجهلون )&lt;/quran_verse&gt; أي : &lt;opinions_of_scholars&gt;تجهلون عظمة الله وجلاله ، وما يجب أن ينزه عنه من الشريك والمثيل&lt;/opinions_of_scholars&gt; .
    &lt;/tafsir_chunk&gt;
&lt;/tafsir_section_block&gt;
&lt;/tafsir_section&gt;
</span></div></div><div class="l" title="&lt;tafsir_section&gt;
&lt;tafsir_section_block&gt;
&lt;tafsir_chunk&gt;
&lt;quran_verse&gt;( إن هؤلاء متبر ما هم فيه )&lt;/quran_verse&gt; أي : &lt;opinions_of_scholars&gt;هالك&lt;/opinions_of_scholars&gt; &lt;quran_verse&gt;( وباطل ما كانوا يعملون )&lt;/quran_verse&gt;
&lt;/tafsir_chunk&gt;
&lt;tafsir_chunk&gt;
      وروى &lt;source&gt;الإمام أبو جعفر بن جرير رحمه الله تفسير هذه الآية من حديث محمد بن إسحاق وعقيل ، ومعمر كلهم ، عن الزهري ، عن سنان بن أبي سنان ، عن أبي واقد الليثي&lt;/source&gt; : أنهم خرجوا من مكة مع رسول الله صلى الله عليه وسلم إلى حنين ، قال : &lt;opinions_of_scholars&gt;وكان للكفار سدرة يعكفون عندها ، ويعلقون بها أسلحتهم ، يقال لها : &quot; ذات أنواط &quot; ، قال : فمررنا بسدرة خضراء عظيمة ، قال : فقلنا : يا رسول الله ، اجعل لنا ذات أنواط كما لهم ذات أنواط . فقال : &quot; قلتم والذي نفسي بيده ، كما قال قوم موسى لموسى : ( اجعل لنا إلها كما لهم آلهة قال إنكم قوم تجهلون إن هؤلاء متبر ما هم فيه وباطل ما كانوا يعملون )&lt;/opinions_of_scholars&gt;
&lt;/tafsir_chunk&gt;
&lt;tafsir_chunk&gt;
      وقال &lt;source&gt;الإمام أحمد : حدثنا عبد الرزاق ، حدثنا معمر ، عن الزهري ، عن سنان بن أبي سنان الديلي ، عن أبي واقد ال" tabindex="0" style="content-visibility: hidden; transform: translate(0px, 2080px); height: 26px;"><div class="Bl"><span>&lt;tafsir_section&gt;
&lt;tafsir_section_block&gt;
&lt;tafsir_chunk&gt;
&lt;quran_verse&gt;( إن هؤلاء متبر ما هم فيه )&lt;/quran_verse&gt; أي : &lt;opinions_of_scholars&gt;هالك&lt;/opinions_of_scholars&gt; &lt;quran_verse&gt;( وباطل ما كانوا يعملون )&lt;/quran_verse&gt;
&lt;/tafsir_chunk&gt;
&lt;tafsir_chunk&gt;
      وروى &lt;source&gt;الإمام أبو جعفر بن جرير رحمه الله تفسير هذه الآية من حديث محمد بن إسحاق وعقيل ، ومعمر كلهم ، عن الزهري ، عن سنان بن أبي سنان ، عن أبي واقد الليثي&lt;/source&gt; : أنهم خرجوا من مكة مع رسول الله صلى الله عليه وسلم إلى حنين ، قال : &lt;opinions_of_scholars&gt;وكان للكفار سدرة يعكفون عندها ، ويعلقون بها أسلحتهم ، يقال لها : " ذات أنواط " ، قال : فمررنا بسدرة خضراء عظيمة ، قال : فقلنا : يا رسول الله ، اجعل لنا ذات أنواط كما لهم ذات أنواط . فقال : " قلتم والذي نفسي بيده ، كما قال قوم موسى لموسى : ( اجعل لنا إلها كما لهم آلهة قال إنكم قوم تجهلون إن هؤلاء متبر ما هم فيه وباطل ما كانوا يعملون )&lt;/opinions_of_scholars&gt;
&lt;/tafsir_chunk&gt;
&lt;tafsir_chunk&gt;
      وقال &lt;source&gt;الإمام أحمد : حدثنا عبد الرزاق ، حدثنا معمر ، عن الزهري ، عن سنان بن أبي سنان الديلي ، عن أبي واقد ال</span></div></div><div class="l Zo" title="&lt;tafsir_section&gt;
&lt;tafsir_section_block&gt;
&lt;tafsir_chunk&gt;
&lt;opinions_of_scholars&gt;يذكرهم موسى ، عليه السلام ، بنعمة الله عليهم ، من إنقاذهم من أسر فرعون وقهره ، وما كانوا فيه من الهوان والذلة ، وما صاروا إليه من العزة والاشتفاء من عدوهم ، والنظر إليه في حال هوانه وهلاكه ، وغرقه ودماره . وقد تقدم تفسيرها في [ سورة ] البقرة&lt;/opinions_of_scholars&gt; .
    &lt;/tafsir_chunk&gt;
&lt;/tafsir_section_block&gt;
&lt;/tafsir_section&gt;
" tabindex="0" style="content-visibility: hidden; transform: translate(0px, 2106px); height: 26px;"><div class="Bl"><span>&lt;tafsir_section&gt;
&lt;tafsir_section_block&gt;
&lt;tafsir_chunk&gt;
&lt;opinions_of_scholars&gt;يذكرهم موسى ، عليه السلام ، بنعمة الله عليهم ، من إنقاذهم من أسر فرعون وقهره ، وما كانوا فيه من الهوان والذلة ، وما صاروا إليه من العزة والاشتفاء من عدوهم ، والنظر إليه في حال هوانه وهلاكه ، وغرقه ودماره . وقد تقدم تفسيرها في [ سورة ] البقرة&lt;/opinions_of_scholars&gt; .
    &lt;/tafsir_chunk&gt;
&lt;/tafsir_section_block&gt;
&lt;/tafsir_section&gt;
</span></div></div><div class="l" title="&lt;tafsir_section&gt;
&lt;tafsir_section_block&gt;
&lt;tafsir_chunk&gt;
&lt;opinions_of_scholars&gt;يذكرهم موسى عليه السلام نعم الله عليهم من إنقاذهم من أسر فرعون وقهره وما كانوا فيه من الهوان والذلة وما صاروا إليه من العزة والاشتفاء من عدوهم والنظر إليه في حال هوانه وهلاكه وغرقة ودماره وقد تقدم تفسيرها في البقرة&lt;/opinions_of_scholars&gt; .
    &lt;/tafsir_chunk&gt;
&lt;/tafsir_section_block&gt;
&lt;/tafsir_section&gt;
" tabindex="0" style="content-visibility: visible; transform: translate(0px, 2132px); height: 26px;"><div class="Bl"><span>&lt;tafsir_section&gt;
&lt;tafsir_section_block&gt;
&lt;tafsir_chunk&gt;
&lt;opinions_of_scholars&gt;يذكرهم موسى عليه السلام نعم الله عليهم من إنقاذهم من أسر فرعون وقهره وما كانوا فيه من الهوان والذلة وما صاروا إليه من العزة والاشتفاء من عدوهم والنظر إليه في حال هوانه وهلاكه وغرقة ودماره وقد تقدم تفسيرها في البقرة&lt;/opinions_of_scholars&gt; .
    &lt;/tafsir_chunk&gt;
&lt;/tafsir_section_block&gt;
&lt;/tafsir_section&gt;
</span></div></div><div class="l Zo" title="&lt;tafsir_section&gt;
&lt;tafsir_section_block&gt;
&lt;tafsir_chunk&gt;
&lt;opinions_of_scholars&gt;يقول تعالى ممتنا على بني إسرائيل ، بما حصل لهم من الهداية ، بتكليمه موسى ، عليه السلام ، وإعطائه التوراة ، وفيها أحكامهم وتفاصيل شرعهم ، فذكر تعالى أنه واعد موسى ثلاثين ليلة . قال المفسرون : فصامها موسى ، عليه السلام ، فلما تم الميقات استاك بلحاء شجرة ، فأمره الله تعالى أن يكمل بعشر أربعين&lt;/opinions_of_scholars&gt; .
    &lt;/tafsir_chunk&gt;
&lt;tafsir_chunk&gt;
&lt;opinions_of_scholars&gt;وقد اختلف المفسرون في هذه العشر ما هي ؟ فالأكثرون على أن الثلاثين هي ذو القعدة ، والعشر عشر ذي الحجة . قاله مجاهد ، ومسروق ، وابن جريج . وروي عن ابن عباس&lt;/opinions_of_scholars&gt; .
    &lt;/tafsir_chunk&gt;
&lt;tafsir_chunk&gt;
&lt;opinions_of_scholars&gt;فعلى هذا يكون قد كمل الميقات يوم النحر ، وحصل فيه التكليم لموسى ، عليه السلام ، وفيه أكمل الله الدين لمحمد صلى الله عليه وسلم&lt;/opinions_of_scholars&gt; ، كما قال تعالى : &lt;cross_references&gt;&lt;quran_verse&gt;( اليوم أكملت لكم دينكم وأتممت عليكم نعمتي ورضيت لكم الإسلام دينا )&lt;/quran_verse&gt; [ المائدة : 3 ]&lt;/cross_references&gt;
&lt;/tafsir_chunk&gt;
&lt;tafsir" tabindex="0" style="content-visibility: visible; transform: translate(0px, 2158px); height: 26px;"><div class="Bl"><span>&lt;tafsir_section&gt;
&lt;tafsir_section_block&gt;
&lt;tafsir_chunk&gt;
&lt;opinions_of_scholars&gt;يقول تعالى ممتنا على بني إسرائيل ، بما حصل لهم من الهداية ، بتكليمه موسى ، عليه السلام ، وإعطائه التوراة ، وفيها أحكامهم وتفاصيل شرعهم ، فذكر تعالى أنه واعد موسى ثلاثين ليلة . قال المفسرون : فصامها موسى ، عليه السلام ، فلما تم الميقات استاك بلحاء شجرة ، فأمره الله تعالى أن يكمل بعشر أربعين&lt;/opinions_of_scholars&gt; .
    &lt;/tafsir_chunk&gt;
&lt;tafsir_chunk&gt;
&lt;opinions_of_scholars&gt;وقد اختلف المفسرون في هذه العشر ما هي ؟ فالأكثرون على أن الثلاثين هي ذو القعدة ، والعشر عشر ذي الحجة . قاله مجاهد ، ومسروق ، وابن جريج . وروي عن ابن عباس&lt;/opinions_of_scholars&gt; .
    &lt;/tafsir_chunk&gt;
&lt;tafsir_chunk&gt;
&lt;opinions_of_scholars&gt;فعلى هذا يكون قد كمل الميقات يوم النحر ، وحصل فيه التكليم لموسى ، عليه السلام ، وفيه أكمل الله الدين لمحمد صلى الله عليه وسلم&lt;/opinions_of_scholars&gt; ، كما قال تعالى : &lt;cross_references&gt;&lt;quran_verse&gt;( اليوم أكملت لكم دينكم وأتممت عليكم نعمتي ورضيت لكم الإسلام دينا )&lt;/quran_verse&gt; [ المائدة : 3 ]&lt;/cross_references&gt;
&lt;/tafsir_chunk&gt;
&lt;tafsir</span></div></div><div class="l" title="&lt;tafsir_section&gt;
&lt;tafsir_section_block&gt;
&lt;tafsir_chunk&gt;
&lt;opinions_of_scholars&gt;يذكر تعالى أنه خاطب موسى عليه السلام بأنه اصطفاه على عالمي زمانه برسالاته وبكلامه تعالى ولا شك أن محمدا صلى الله عليه وسلم سيد ولد آدم من الأولين والآخرين ; ولهذا اختصه الله بأن جعله خاتم الأنبياء والمرسلين ، التي تستمر شريعته إلى قيام الساعة ، وأتباعه أكثر من أتباع سائر الأنبياء والمرسلين كلهم ، وبعده في الشرف والفضل إبراهيم الخليل ، عليه السلام ، ثم موسى بن عمران كليم الرحمن ، عليه السلام&lt;/opinions_of_scholars&gt; ; ولهذا قال الله تعالى له : &lt;quran_verse&gt;( فخذ ما آتيتك )&lt;/quran_verse&gt; أي : &lt;opinions_of_scholars&gt;من الكلام والوحي والمناجاة&lt;/opinions_of_scholars&gt; &lt;quran_verse&gt;( وكن من الشاكرين )&lt;/quran_verse&gt; أي : &lt;opinions_of_scholars&gt;على ذلك ، ولا تطلب ما لا طاقة لك به&lt;/opinions_of_scholars&gt; .
    &lt;/tafsir_chunk&gt;
&lt;/tafsir_section_block&gt;
&lt;/tafsir_section&gt;
" tabindex="0" style="content-visibility: visible; transform: translate(0px, 2184px); height: 26px;"><div class="Bl"><span>&lt;tafsir_section&gt;
&lt;tafsir_section_block&gt;
&lt;tafsir_chunk&gt;
&lt;opinions_of_scholars&gt;يذكر تعالى أنه خاطب موسى عليه السلام بأنه اصطفاه على عالمي زمانه برسالاته وبكلامه تعالى ولا شك أن محمدا صلى الله عليه وسلم سيد ولد آدم من الأولين والآخرين ; ولهذا اختصه الله بأن جعله خاتم الأنبياء والمرسلين ، التي تستمر شريعته إلى قيام الساعة ، وأتباعه أكثر من أتباع سائر الأنبياء والمرسلين كلهم ، وبعده في الشرف والفضل إبراهيم الخليل ، عليه السلام ، ثم موسى بن عمران كليم الرحمن ، عليه السلام&lt;/opinions_of_scholars&gt; ; ولهذا قال الله تعالى له : &lt;quran_verse&gt;( فخذ ما آتيتك )&lt;/quran_verse&gt; أي : &lt;opinions_of_scholars&gt;من الكلام والوحي والمناجاة&lt;/opinions_of_scholars&gt; &lt;quran_verse&gt;( وكن من الشاكرين )&lt;/quran_verse&gt; أي : &lt;opinions_of_scholars&gt;على ذلك ، ولا تطلب ما لا طاقة لك به&lt;/opinions_of_scholars&gt; .
    &lt;/tafsir_chunk&gt;
&lt;/tafsir_section_block&gt;
&lt;/tafsir_section&gt;
</span></div></div><div class="l Zo" title="&lt;tafsir_section&gt;
&lt;tafsir_section_block&gt;
&lt;tafsir_chunk&gt;
&lt;opinions_of_scholars&gt;ثم أخبر تعالى أنه كتب له في الألواح من كل شيء موعظة وتفصيلا لكل شيء ، قيل : كانت الألواح من جوهر ، وأن الله تعالى كتب له فيها مواعظ وأحكاما مفصلة مبينة للحلال والحرام ، وكانت هذه الألواح مشتملة على التوراة التي قال الله تعالى فيها :&lt;/opinions_of_scholars&gt; &lt;cross_references&gt;&lt;quran_verse&gt;( ولقد آتينا موسى الكتاب من بعد ما أهلكنا القرون الأولى بصائر للناس )&lt;/quran_verse&gt; [ القصص : 43 ]&lt;/cross_references&gt; &lt;opinions_of_scholars&gt;وقيل : الألواح أعطيها موسى قبل التوراة ، فالله أعلم . وعلى كل تقدير كانت كالتعويض له عما سأل من الرؤية ومنع منه ، والله أعلم&lt;/opinions_of_scholars&gt; .
    &lt;/tafsir_chunk&gt;
&lt;tafsir_chunk&gt;
      وقوله : &lt;quran_verse&gt;( فخذها بقوة )&lt;/quran_verse&gt; أي : &lt;opinions_of_scholars&gt;بعزم على الطاعة&lt;/opinions_of_scholars&gt; &lt;quran_verse&gt;( وأمر قومك يأخذوا بأحسنها )&lt;/quran_verse&gt; قال &lt;opinions_of_scholars&gt;سفيان بن عيينة : حدثنا أبو سعد عن عكرمة ، عن ابن عباس&lt;/opinions_of_scholars&gt; قال : &lt;opinions_of_scholars&gt;أمر موسى - عليه السلام - أ" tabindex="0" style="content-visibility: visible; transform: translate(0px, 2210px); height: 26px;"><div class="Bl"><span>&lt;tafsir_section&gt;
&lt;tafsir_section_block&gt;
&lt;tafsir_chunk&gt;
&lt;opinions_of_scholars&gt;ثم أخبر تعالى أنه كتب له في الألواح من كل شيء موعظة وتفصيلا لكل شيء ، قيل : كانت الألواح من جوهر ، وأن الله تعالى كتب له فيها مواعظ وأحكاما مفصلة مبينة للحلال والحرام ، وكانت هذه الألواح مشتملة على التوراة التي قال الله تعالى فيها :&lt;/opinions_of_scholars&gt; &lt;cross_references&gt;&lt;quran_verse&gt;( ولقد آتينا موسى الكتاب من بعد ما أهلكنا القرون الأولى بصائر للناس )&lt;/quran_verse&gt; [ القصص : 43 ]&lt;/cross_references&gt; &lt;opinions_of_scholars&gt;وقيل : الألواح أعطيها موسى قبل التوراة ، فالله أعلم . وعلى كل تقدير كانت كالتعويض له عما سأل من الرؤية ومنع منه ، والله أعلم&lt;/opinions_of_scholars&gt; .
    &lt;/tafsir_chunk&gt;
&lt;tafsir_chunk&gt;
      وقوله : &lt;quran_verse&gt;( فخذها بقوة )&lt;/quran_verse&gt; أي : &lt;opinions_of_scholars&gt;بعزم على الطاعة&lt;/opinions_of_scholars&gt; &lt;quran_verse&gt;( وأمر قومك يأخذوا بأحسنها )&lt;/quran_verse&gt; قال &lt;opinions_of_scholars&gt;سفيان بن عيينة : حدثنا أبو سعد عن عكرمة ، عن ابن عباس&lt;/opinions_of_scholars&gt; قال : &lt;opinions_of_scholars&gt;أمر موسى - عليه السلام - أ</span></div></div><div class="l" title="&lt;tafsir_section&gt;
&lt;tafsir_section_block&gt;
&lt;tafsir_chunk&gt;
      يقول تعالى : &lt;quran_verse&gt;( سأصرف عن آياتي الذين يتكبرون في الأرض بغير الحق )&lt;/quran_verse&gt; أي : &lt;opinions_of_scholars&gt;سأمنع فهم الحجج والأدلة على عظمتي وشريعتي وأحكامي قلوب المتكبرين عن طاعتي ، ويتكبرون على الناس بغير حق ، أي : كما استكبروا بغير حق أذلهم الله بالجهل&lt;/opinions_of_scholars&gt; ، كما قال تعالى : &lt;cross_references&gt;&lt;quran_verse&gt;( ونقلب أفئدتهم وأبصارهم كما لم يؤمنوا به أول مرة )&lt;/quran_verse&gt; [ الأنعام : 110 ]&lt;/cross_references&gt; وقال تعالى : &lt;cross_references&gt;&lt;quran_verse&gt;( فلما زاغوا أزاغ الله قلوبهم )&lt;/quran_verse&gt; [ الصف : 5 ]&lt;/cross_references&gt;
&lt;/tafsir_chunk&gt;
&lt;tafsir_chunk&gt;
      وقال &lt;opinions_of_scholars&gt;بعض السلف : لا ينال العلم حيي ولا مستكبر . وقال آخر : من لم يصبر على ذل التعلم ساعة ، بقي في ذل الجهل أبدا&lt;/opinions_of_scholars&gt; .
    &lt;/tafsir_chunk&gt;
&lt;tafsir_chunk&gt;
      وقال &lt;opinions_of_scholars&gt;سفيان بن عيينة&lt;/opinions_of_scholars&gt; في قوله : &lt;quran_verse&gt;( سأصرف عن آياتي الذين يتكبرون في الأرض bغير الحق )&lt;/quran_verse&gt; قال : &lt;" tabindex="0" style="content-visibility: visible; transform: translate(0px, 2236px); height: 26px;"><div class="Bl"><span>&lt;tafsir_section&gt;
&lt;tafsir_section_block&gt;
&lt;tafsir_chunk&gt;
      يقول تعالى : &lt;quran_verse&gt;( سأصرف عن آياتي الذين يتكبرون في الأرض بغير الحق )&lt;/quran_verse&gt; أي : &lt;opinions_of_scholars&gt;سأمنع فهم الحجج والأدلة على عظمتي وشريعتي وأحكامي قلوب المتكبرين عن طاعتي ، ويتكبرون على الناس بغير حق ، أي : كما استكبروا بغير حق أذلهم الله بالجهل&lt;/opinions_of_scholars&gt; ، كما قال تعالى : &lt;cross_references&gt;&lt;quran_verse&gt;( ونقلب أفئدتهم وأبصارهم كما لم يؤمنوا به أول مرة )&lt;/quran_verse&gt; [ الأنعام : 110 ]&lt;/cross_references&gt; وقال تعالى : &lt;cross_references&gt;&lt;quran_verse&gt;( فلما زاغوا أزاغ الله قلوبهم )&lt;/quran_verse&gt; [ الصف : 5 ]&lt;/cross_references&gt;
&lt;/tafsir_chunk&gt;
&lt;tafsir_chunk&gt;
      وقال &lt;opinions_of_scholars&gt;بعض السلف : لا ينال العلم حيي ولا مستكبر . وقال آخر : من لم يصبر على ذل التعلم ساعة ، بقي في ذل الجهل أبدا&lt;/opinions_of_scholars&gt; .
    &lt;/tafsir_chunk&gt;
&lt;tafsir_chunk&gt;
      وقال &lt;opinions_of_scholars&gt;سفيان بن عيينة&lt;/opinions_of_scholars&gt; في قوله : &lt;quran_verse&gt;( سأصرف عن آياتي الذين يتكبرون في الأرض bغير الحق )&lt;/quran_verse&gt; قال : &lt;</span></div></div><div class="l Zo" title="&lt;tafsir_section&gt;
&lt;tafsir_section_block&gt;
&lt;tafsir_chunk&gt;
      وقوله : &lt;quran_verse&gt;( والذين كذبوا بآياتنا ولقاء الآخرة حبطت أعمالهم )&lt;/quran_verse&gt; أي : &lt;opinions_of_scholars&gt;من فعل منهم ذلك واستمر عليه إلى الممات ، حبط عمله&lt;/opinions_of_scholars&gt; . 
    &lt;/tafsir_chunk&gt;
&lt;tafsir_chunk&gt;
      وقوله : &lt;quran_verse&gt;( هل يجزون إلا ما كانوا يعملون )&lt;/quran_verse&gt; أي : &lt;opinions_of_scholars&gt;إنما نجازيهم بحسب أعمالهم التي أسلفوها ، إن خيرا فخير وإن شرا فشر ، وكما تدين تدان&lt;/opinions_of_scholars&gt; .
    &lt;/tafsir_chunk&gt;
&lt;/tafsir_section_block&gt;
&lt;/tafsir_section&gt;
" tabindex="0" style="content-visibility: visible; transform: translate(0px, 2262px); height: 26px;"><div class="Bl"><span>&lt;tafsir_section&gt;
&lt;tafsir_section_block&gt;
&lt;tafsir_chunk&gt;
      وقوله : &lt;quran_verse&gt;( والذين كذبوا بآياتنا ولقاء الآخرة حبطت أعمالهم )&lt;/quran_verse&gt; أي : &lt;opinions_of_scholars&gt;من فعل منهم ذلك واستمر عليه إلى الممات ، حبط عمله&lt;/opinions_of_scholars&gt; . 
    &lt;/tafsir_chunk&gt;
&lt;tafsir_chunk&gt;
      وقوله : &lt;quran_verse&gt;( هل يجزون إلا ما كانوا يعملون )&lt;/quran_verse&gt; أي : &lt;opinions_of_scholars&gt;إنما نجازيهم بحسب أعمالهم التي أسلفوها ، إن خيرا فخير وإن شرا فشر ، وكما تدين تدان&lt;/opinions_of_scholars&gt; .
    &lt;/tafsir_chunk&gt;
&lt;/tafsir_section_block&gt;
&lt;/tafsir_section&gt;
</span></div></div><div class="l" title="&lt;tafsir_section&gt;
&lt;tafsir_section_block&gt;
&lt;tafsir_chunk&gt;
&lt;opinions_of_scholars&gt;يخبر تعالى عن ضلال من ضل من بني إسرائيل في عبادتهم العجل ، الذي اتخذه لهم السامري من حلي القبط ، الذي كانوا استعاروه منهم ، فشكل لهم منه عجلا ثم ألقى فيه القبضة من التراب التي أخذها من أثر فرس جبريل ، عليه السلام ، فصار عجلا جسدا له خوار ، و &quot; الخوار &quot; صوت البقر . وكان هذا منهم بعد ذهاب موسى عليه السلام لميقات ربه تعالى ، وأعلمه الله تعالى بذلك وهو على الطور&lt;/opinions_of_scholars&gt; ، حيث يقول تعالى إخبارا عن نفسه الكريمة : &lt;cross_references&gt;&lt;quran_verse&gt;( قال فإنا قد فتنا قومك من بعدك وأضلهم السامري )&lt;/quran_verse&gt; [ طه : 85 ]&lt;/cross_references&gt;
&lt;/tafsir_chunk&gt;
&lt;tafsir_chunk&gt;
&lt;opinions_of_scholars&gt;وقد اختلف المفسرون في هذا العجل : هل صار لحما ودما له خوار ؟ أو استمر على كونه من ذهب ، إلا أنه يدخل فيه الهواء فيصوت كالبقر ؟ على قولين ، والله أعلم . ويقال : إنهم لما صوت لهم العجل رقصوا حوله وافتتنوا به ،&lt;/opinions_of_scholars&gt; &lt;cross_references&gt;&lt;quran_verse&gt;( فقالوا هذا إلهكم وإله موسى فنسي )&lt;/quran_verse&gt; [ طه : 88 ]&lt;/cross_references&gt; " tabindex="0" style="content-visibility: visible; transform: translate(0px, 2288px); height: 26px;"><div class="Bl"><span>&lt;tafsir_section&gt;
&lt;tafsir_section_block&gt;
&lt;tafsir_chunk&gt;
&lt;opinions_of_scholars&gt;يخبر تعالى عن ضلال من ضل من بني إسرائيل في عبادتهم العجل ، الذي اتخذه لهم السامري من حلي القبط ، الذي كانوا استعاروه منهم ، فشكل لهم منه عجلا ثم ألقى فيه القبضة من التراب التي أخذها من أثر فرس جبريل ، عليه السلام ، فصار عجلا جسدا له خوار ، و " الخوار " صوت البقر . وكان هذا منهم بعد ذهاب موسى عليه السلام لميقات ربه تعالى ، وأعلمه الله تعالى بذلك وهو على الطور&lt;/opinions_of_scholars&gt; ، حيث يقول تعالى إخبارا عن نفسه الكريمة : &lt;cross_references&gt;&lt;quran_verse&gt;( قال فإنا قد فتنا قومك من بعدك وأضلهم السامري )&lt;/quran_verse&gt; [ طه : 85 ]&lt;/cross_references&gt;
&lt;/tafsir_chunk&gt;
&lt;tafsir_chunk&gt;
&lt;opinions_of_scholars&gt;وقد اختلف المفسرون في هذا العجل : هل صار لحما ودما له خوار ؟ أو استمر على كونه من ذهب ، إلا أنه يدخل فيه الهواء فيصوت كالبقر ؟ على قولين ، والله أعلم . ويقال : إنهم لما صوت لهم العجل رقصوا حوله وافتتنوا به ،&lt;/opinions_of_scholars&gt; &lt;cross_references&gt;&lt;quran_verse&gt;( فقالوا هذا إلهكم وإله موسى فنسي )&lt;/quran_verse&gt; [ طه : 88 ]&lt;/cross_references&gt; </span></div></div><div class="l Zo" title="&lt;tafsir_section&gt;
&lt;tafsir_section_block&gt;
&lt;tafsir_chunk&gt;
      وقوله : &lt;quran_verse&gt;( ولما سقط في أيديهم )&lt;/quran_verse&gt; أي : &lt;opinions_of_scholars&gt;ندموا على ما فعلوا&lt;/opinions_of_scholars&gt; ، &lt;quran_verse&gt;( ورأوا أنهم قد ضلوا قالوا لئن لم يرحمنا ربنا ويغفر لنا )&lt;/quran_verse&gt;
&lt;/tafsir_chunk&gt;
&lt;tafsir_chunk&gt;
&lt;opinions_of_scholars&gt;وقرأ بعضهم : &quot; لئن لم ترحمنا &quot; بالتاء المثناة من فوق ، &quot; ربنا &quot; منادى ، &quot; وتغفر لنا &quot;&lt;/opinions_of_scholars&gt; ، &lt;quran_verse&gt;( لنكونن من الخاسرين )&lt;/quran_verse&gt; أي : &lt;opinions_of_scholars&gt;من الهالكين وهذا اعتراف منهم بذنبهم والتجاء إلى الله عز وجل&lt;/opinions_of_scholars&gt; .
    &lt;/tafsir_chunk&gt;
&lt;/tafsir_section_block&gt;
&lt;/tafsir_section&gt;
" tabindex="0" style="content-visibility: visible; transform: translate(0px, 2314px); height: 26px;"><div class="Bl"><span>&lt;tafsir_section&gt;
&lt;tafsir_section_block&gt;
&lt;tafsir_chunk&gt;
      وقوله : &lt;quran_verse&gt;( ولما سقط في أيديهم )&lt;/quran_verse&gt; أي : &lt;opinions_of_scholars&gt;ندموا على ما فعلوا&lt;/opinions_of_scholars&gt; ، &lt;quran_verse&gt;( ورأوا أنهم قد ضلوا قالوا لئن لم يرحمنا ربنا ويغفر لنا )&lt;/quran_verse&gt;
&lt;/tafsir_chunk&gt;
&lt;tafsir_chunk&gt;
&lt;opinions_of_scholars&gt;وقرأ بعضهم : " لئن لم ترحمنا " بالتاء المثناة من فوق ، " ربنا " منادى ، " وتغفر لنا "&lt;/opinions_of_scholars&gt; ، &lt;quran_verse&gt;( لنكونن من الخاسرين )&lt;/quran_verse&gt; أي : &lt;opinions_of_scholars&gt;من الهالكين وهذا اعتراف منهم بذنبهم والتجاء إلى الله عز وجل&lt;/opinions_of_scholars&gt; .
    &lt;/tafsir_chunk&gt;
&lt;/tafsir_section_block&gt;
&lt;/tafsir_section&gt;
</span></div></div><div class="l" title="&lt;tafsir_section&gt;
&lt;tafsir_section_block&gt;
&lt;tafsir_chunk&gt;
&lt;opinions_of_scholars&gt;يخبر تعالى أن موسى ، عليه السلام ، رجع إلى قومه من مناجاة ربه تعالى وهو غضبان أسف .&lt;/opinions_of_scholars&gt; قال &lt;opinions_of_scholars&gt;أبو الدرداء &quot; الأسف &quot; : أشد الغضب .&lt;/opinions_of_scholars&gt; &lt;quran_verse&gt;( قال بئسما خلفتموني من بعدي )&lt;/quran_verse&gt; يقول : &lt;opinions_of_scholars&gt;بئس ما صنعتم في عبادتكم العجل بعد أن ذهبت وتركتكم .&lt;/opinions_of_scholars&gt; وقوله : &lt;quran_verse&gt;( أعجلتم أمر ربكم )&lt;/quran_verse&gt; ؟ يقول : &lt;opinions_of_scholars&gt;استعجلتم مجيئي إليكم ، وهو مقدر من الله تعالى .&lt;/opinions_of_scholars&gt;
&lt;/tafsir_chunk&gt;
&lt;tafsir_chunk&gt;
      وقوله : &lt;quran_verse&gt;( وألقى الألواح وأخذ برأس أخيه يجره إليه )&lt;/quran_verse&gt; &lt;opinions_of_scholars&gt;قيل : كانت الألواح من زمرد . وقيل : من ياقوت . وقيل : من برد وفي هذا دلالة على ما جاء في الحديث : &quot; ليس الخبر كالمعاينة &quot; ثم ظاهر السياق أنه إنما ألقى الألواح غضبا على قومه ، وهذا قول جمهور العلماء سلفا وخلفا .&lt;/opinions_of_scholars&gt; &lt;source&gt;وروى ابن جرير عن قتادة في هذا قولا غريبا ، لا يصح إسناده " tabindex="0" style="content-visibility: visible; transform: translate(0px, 2340px); height: 26px;"><div class="Bl"><span>&lt;tafsir_section&gt;
&lt;tafsir_section_block&gt;
&lt;tafsir_chunk&gt;
&lt;opinions_of_scholars&gt;يخبر تعالى أن موسى ، عليه السلام ، رجع إلى قومه من مناجاة ربه تعالى وهو غضبان أسف .&lt;/opinions_of_scholars&gt; قال &lt;opinions_of_scholars&gt;أبو الدرداء " الأسف " : أشد الغضب .&lt;/opinions_of_scholars&gt; &lt;quran_verse&gt;( قال بئسما خلفتموني من بعدي )&lt;/quran_verse&gt; يقول : &lt;opinions_of_scholars&gt;بئس ما صنعتم في عبادتكم العجل بعد أن ذهبت وتركتكم .&lt;/opinions_of_scholars&gt; وقوله : &lt;quran_verse&gt;( أعجلتم أمر ربكم )&lt;/quran_verse&gt; ؟ يقول : &lt;opinions_of_scholars&gt;استعجلتم مجيئي إليكم ، وهو مقدر من الله تعالى .&lt;/opinions_of_scholars&gt;
&lt;/tafsir_chunk&gt;
&lt;tafsir_chunk&gt;
      وقوله : &lt;quran_verse&gt;( وألقى الألواح وأخذ برأس أخيه يجره إليه )&lt;/quran_verse&gt; &lt;opinions_of_scholars&gt;قيل : كانت الألواح من زمرد . وقيل : من ياقوت . وقيل : من برد وفي هذا دلالة على ما جاء في الحديث : " ليس الخبر كالمعاينة " ثم ظاهر السياق أنه إنما ألقى الألواح غضبا على قومه ، وهذا قول جمهور العلماء سلفا وخلفا .&lt;/opinions_of_scholars&gt; &lt;source&gt;وروى ابن جرير عن قتادة في هذا قولا غريبا ، لا يصح إسناده </span></div></div><div class="l Zo" title="&lt;tafsir_section&gt;
&lt;tafsir_section_block&gt;
&lt;tafsir_chunk&gt;
      فعند ذلك قال موسى : &lt;quran_verse&gt;( رب اغفر لي ولأخي وأدخلنا في رحمتك وأنت أرحم الراحمين )&lt;/quran_verse&gt;
&lt;/tafsir_chunk&gt;
&lt;tafsir_chunk&gt;
      قال &lt;source&gt;ابن أبي حاتم : حدثنا الحسن بن محمد بن الصباح ، حدثنا عفان ، حدثنا أبو عوانة ، عن أبي بشر ، عن سعيد بن جبير ، عن ابن عباس&lt;/source&gt; قال : قال النبي صلى الله عليه وسلم &lt;opinions_of_scholars&gt;&quot; يرحم الله موسى ، ليس المعاين كالمخبر ; أخبره ربه ، عز وجل ، أن قومه فتنوا بعده ، فلم يلق الألواح ، فلما رآهم وعاينهم ألقى الألواح &quot;&lt;/opinions_of_scholars&gt;
&lt;/tafsir_chunk&gt;
&lt;/tafsir_section_block&gt;
&lt;/tafsir_section&gt;
" tabindex="0" style="content-visibility: visible; transform: translate(0px, 2366px); height: 26px;"><div class="Bl"><span>&lt;tafsir_section&gt;
&lt;tafsir_section_block&gt;
&lt;tafsir_chunk&gt;
      فعند ذلك قال موسى : &lt;quran_verse&gt;( رب اغفر لي ولأخي وأدخلنا في رحمتك وأنت أرحم الراحمين )&lt;/quran_verse&gt;
&lt;/tafsir_chunk&gt;
&lt;tafsir_chunk&gt;
      قال &lt;source&gt;ابن أبي حاتم : حدثنا الحسن بن محمد بن الصباح ، حدثنا عفان ، حدثنا أبو عوانة ، عن أبي بشر ، عن سعيد بن جبير ، عن ابن عباس&lt;/source&gt; قال : قال النبي صلى الله عليه وسلم &lt;opinions_of_scholars&gt;" يرحم الله موسى ، ليس المعاين كالمخبر ; أخبره ربه ، عز وجل ، أن قومه فتنوا بعده ، فلم يلق الألواح ، فلما رآهم وعاينهم ألقى الألواح "&lt;/opinions_of_scholars&gt;
&lt;/tafsir_chunk&gt;
&lt;/tafsir_section_block&gt;
&lt;/tafsir_section&gt;
</span></div></div><div class="l" title="&lt;tafsir_section&gt;
&lt;tafsir_section_block&gt;
&lt;tafsir_chunk&gt;
&lt;opinions_of_scholars&gt;أما الغضب الذي نال بني إسرائيل في عبادة العجل ، فهو أن الله تعالى لم يقبل لهم توبة ، حتى قتل بعضهم بعضا ،&lt;/opinions_of_scholars&gt; كما تقدم في سورة البقرة : &lt;cross_references&gt;&lt;quran_verse&gt;( فتوبوا إلى بارئكم فاقتلوا أنفسكم ذلكم خير لكم عند بارئكم فتاب عليكم إنه هو التواب الرحيم )&lt;/quran_verse&gt; [ البقرة : 54 ]&lt;/cross_references&gt; &lt;opinions_of_scholars&gt;وأما الذلة فأعقبهم ذلك ذلا وصغارا في الحياة الدنيا&lt;/opinions_of_scholars&gt; .
    &lt;/tafsir_chunk&gt;
&lt;tafsir_chunk&gt;
      وقوله : &lt;quran_verse&gt;( وكذلك نجزي المفترين )&lt;/quran_verse&gt; &lt;opinions_of_scholars&gt;نائلة لكل من افترى بدعة ، فإن ذل البدعة ومخالفة الرسالة متصلة من قلبه على كتفيه ،&lt;/opinions_of_scholars&gt; كما قال &lt;opinions_of_scholars&gt;الحسن البصري : إن ذل البدعة على أكتافهم ، وإن هملجت بهم البغلات ، وطقطقت بهم البراذين&lt;/opinions_of_scholars&gt; . 
    &lt;/tafsir_chunk&gt;
&lt;tafsir_chunk&gt;
      وهكذا روى &lt;source&gt;أيوب السختياني ، عن أبي قلابة الجرمي&lt;/source&gt; ، أنه قرأ هذه الآية : &lt;quran_verse&gt;( وكذلك نجزي" tabindex="0" style="content-visibility: visible; transform: translate(0px, 2392px); height: 26px;"><div class="Bl"><span>&lt;tafsir_section&gt;
&lt;tafsir_section_block&gt;
&lt;tafsir_chunk&gt;
&lt;opinions_of_scholars&gt;أما الغضب الذي نال بني إسرائيل في عبادة العجل ، فهو أن الله تعالى لم يقبل لهم توبة ، حتى قتل بعضهم بعضا ،&lt;/opinions_of_scholars&gt; كما تقدم في سورة البقرة : &lt;cross_references&gt;&lt;quran_verse&gt;( فتوبوا إلى بارئكم فاقتلوا أنفسكم ذلكم خير لكم عند بارئكم فتاب عليكم إنه هو التواب الرحيم )&lt;/quran_verse&gt; [ البقرة : 54 ]&lt;/cross_references&gt; &lt;opinions_of_scholars&gt;وأما الذلة فأعقبهم ذلك ذلا وصغارا في الحياة الدنيا&lt;/opinions_of_scholars&gt; .
    &lt;/tafsir_chunk&gt;
&lt;tafsir_chunk&gt;
      وقوله : &lt;quran_verse&gt;( وكذلك نجزي المفترين )&lt;/quran_verse&gt; &lt;opinions_of_scholars&gt;نائلة لكل من افترى بدعة ، فإن ذل البدعة ومخالفة الرسالة متصلة من قلبه على كتفيه ،&lt;/opinions_of_scholars&gt; كما قال &lt;opinions_of_scholars&gt;الحسن البصري : إن ذل البدعة على أكتافهم ، وإن هملجت بهم البغلات ، وطقطقت بهم البراذين&lt;/opinions_of_scholars&gt; . 
    &lt;/tafsir_chunk&gt;
&lt;tafsir_chunk&gt;
      وهكذا روى &lt;source&gt;أيوب السختياني ، عن أبي قلابة الجرمي&lt;/source&gt; ، أنه قرأ هذه الآية : &lt;quran_verse&gt;( وكذلك نجزي</span></div></div><div class="l Zo" title="&lt;tafsir_section&gt;
&lt;tafsir_section_block&gt;
&lt;tafsir_chunk&gt;
&lt;opinions_of_scholars&gt;ثم نبه تعالى عباده وأرشدهم إلى أنه يقبل توبة عباده من أي ذنب كان ، حتى ولو كان من كفر أو شرك أو نفاق أو شقاق ; ولهذا عقب هذه القصة بقوله :&lt;/opinions_of_scholars&gt; &lt;quran_verse&gt;( والذين عملوا السيئات ثم تابوا من بعدها وآمنوا إن ربك )&lt;/quran_verse&gt; أي : &lt;opinions_of_scholars&gt;يا محمد ، يا رسول الرحمة ونبي النور&lt;/opinions_of_scholars&gt; &lt;quran_verse&gt;( من بعدها )&lt;/quran_verse&gt; أي : &lt;opinions_of_scholars&gt;من بعد تلك الفعلة&lt;/opinions_of_scholars&gt; &lt;quran_verse&gt;( لغفور رحيم )&lt;/quran_verse&gt;
&lt;/tafsir_chunk&gt;
&lt;tafsir_chunk&gt;
      وقال &lt;source&gt;ابن أبي حاتم : حدثنا أبي ، حدثنا مسلم بن إبراهيم ، حدثنا أبان ، حدثنا قتادة ، عن عزرة عن الحسن العرفي ، عن علقمة ، عن عبد الله بن مسعود&lt;/source&gt; ; &lt;opinions_of_scholars&gt;أنه سئل عن ذلك - يعني عن الرجل يزني بالمرأة ، ثم يتزوجها - فتلا هذه الآية :&lt;/opinions_of_scholars&gt; &lt;quran_verse&gt;( والذين عملوا السيئات ثم تابوا من بعدها وآمنوا إن ربك من بعدها لغفور رحيم )&lt;/quran_verse&gt; &lt;opinions_of_scholars&gt;فتلاها عبد الله عشر م" tabindex="0" style="content-visibility: visible; transform: translate(0px, 2418px); height: 26px;"><div class="Bl"><span>&lt;tafsir_section&gt;
&lt;tafsir_section_block&gt;
&lt;tafsir_chunk&gt;
&lt;opinions_of_scholars&gt;ثم نبه تعالى عباده وأرشدهم إلى أنه يقبل توبة عباده من أي ذنب كان ، حتى ولو كان من كفر أو شرك أو نفاق أو شقاق ; ولهذا عقب هذه القصة بقوله :&lt;/opinions_of_scholars&gt; &lt;quran_verse&gt;( والذين عملوا السيئات ثم تابوا من بعدها وآمنوا إن ربك )&lt;/quran_verse&gt; أي : &lt;opinions_of_scholars&gt;يا محمد ، يا رسول الرحمة ونبي النور&lt;/opinions_of_scholars&gt; &lt;quran_verse&gt;( من بعدها )&lt;/quran_verse&gt; أي : &lt;opinions_of_scholars&gt;من بعد تلك الفعلة&lt;/opinions_of_scholars&gt; &lt;quran_verse&gt;( لغفور رحيم )&lt;/quran_verse&gt;
&lt;/tafsir_chunk&gt;
&lt;tafsir_chunk&gt;
      وقال &lt;source&gt;ابن أبي حاتم : حدثنا أبي ، حدثنا مسلم بن إبراهيم ، حدثنا أبان ، حدثنا قتادة ، عن عزرة عن الحسن العرفي ، عن علقمة ، عن عبد الله بن مسعود&lt;/source&gt; ; &lt;opinions_of_scholars&gt;أنه سئل عن ذلك - يعني عن الرجل يزني بالمرأة ، ثم يتزوجها - فتلا هذه الآية :&lt;/opinions_of_scholars&gt; &lt;quran_verse&gt;( والذين عملوا السيئات ثم تابوا من بعدها وآمنوا إن ربك من بعدها لغفور رحيم )&lt;/quran_verse&gt; &lt;opinions_of_scholars&gt;فتلاها عبد الله عشر م</span></div></div><div class="l" title="&lt;tafsir_section&gt;
&lt;tafsir_section_block&gt;
&lt;tafsir_chunk&gt;
      يقول تعالى : &lt;quran_verse&gt;( ولما سكت )&lt;/quran_verse&gt; أي : &lt;opinions_of_scholars&gt;سكن&lt;/opinions_of_scholars&gt; &lt;quran_verse&gt;( عن موسى الغضب )&lt;/quran_verse&gt; أي : &lt;opinions_of_scholars&gt;غضبه على قومه&lt;/opinions_of_scholars&gt; &lt;quran_verse&gt;( أخذ الألواح )&lt;/quran_verse&gt; أي : &lt;opinions_of_scholars&gt;التي كان ألقاها من شدة الغضب على عبادتهم العجل ، غيرة لله وغضبا له&lt;/opinions_of_scholars&gt; &lt;quran_verse&gt;( وفي نسختها هدى ورحمة )&lt;/quran_verse&gt; .
    &lt;/tafsir_chunk&gt;
&lt;tafsir_chunk&gt;
&lt;opinions_of_scholars&gt;يقول كثير من المفسرين : إنها لما ألقاها تكسرت ، ثم جمعها بعد ذلك ; ولهذا قال بعض السلف : فوجد فيها هدى ورحمة . وأما التفصيل فذهب ، وزعموا أن رضاضها لم يزل موجودا في خزائن الملوك لبني إسرائيل إلى الدولة الإسلامية ، والله أعلم بصحة هذا&lt;/opinions_of_scholars&gt; .
    &lt;/tafsir_chunk&gt;
&lt;tafsir_chunk&gt;
&lt;quran_verse&gt;( للذين هم لربهم يرهبون )&lt;/quran_verse&gt; &lt;opinions_of_scholars&gt;ضمن الرهبة معنى الخضوع ; ولهذا عداها باللام&lt;/opinions_of_scholars&gt; .
    &lt;/tafsir_chunk&gt;
&lt;tafsir_chunk&gt;
   " tabindex="0" style="content-visibility: visible; transform: translate(0px, 2444px); height: 26px;"><div class="Bl"><span>&lt;tafsir_section&gt;
&lt;tafsir_section_block&gt;
&lt;tafsir_chunk&gt;
      يقول تعالى : &lt;quran_verse&gt;( ولما سكت )&lt;/quran_verse&gt; أي : &lt;opinions_of_scholars&gt;سكن&lt;/opinions_of_scholars&gt; &lt;quran_verse&gt;( عن موسى الغضب )&lt;/quran_verse&gt; أي : &lt;opinions_of_scholars&gt;غضبه على قومه&lt;/opinions_of_scholars&gt; &lt;quran_verse&gt;( أخذ الألواح )&lt;/quran_verse&gt; أي : &lt;opinions_of_scholars&gt;التي كان ألقاها من شدة الغضب على عبادتهم العجل ، غيرة لله وغضبا له&lt;/opinions_of_scholars&gt; &lt;quran_verse&gt;( وفي نسختها هدى ورحمة )&lt;/quran_verse&gt; .
    &lt;/tafsir_chunk&gt;
&lt;tafsir_chunk&gt;
&lt;opinions_of_scholars&gt;يقول كثير من المفسرين : إنها لما ألقاها تكسرت ، ثم جمعها بعد ذلك ; ولهذا قال بعض السلف : فوجد فيها هدى ورحمة . وأما التفصيل فذهب ، وزعموا أن رضاضها لم يزل موجودا في خزائن الملوك لبني إسرائيل إلى الدولة الإسلامية ، والله أعلم بصحة هذا&lt;/opinions_of_scholars&gt; .
    &lt;/tafsir_chunk&gt;
&lt;tafsir_chunk&gt;
&lt;quran_verse&gt;( للذين هم لربهم يرهبون )&lt;/quran_verse&gt; &lt;opinions_of_scholars&gt;ضمن الرهبة معنى الخضوع ; ولهذا عداها باللام&lt;/opinions_of_scholars&gt; .
    &lt;/tafsir_chunk&gt;
&lt;tafsir_chunk&gt;
   </span></div></div><div class="l Zo" title="&lt;tafsir_section&gt;
&lt;tafsir_section_block&gt;
&lt;tafsir_chunk&gt;
      قال &lt;source&gt;علي بن أبي طلحة ، عن ابن عباس&lt;/source&gt; في تفسير هذه الآية : &lt;opinions_of_scholars&gt;كان الله أمره أن يختار من قومه سبعين رجلا فاختار سبعين رجلا فبرز بهم ليدعوا ربهم ، فكان فيما دعوا الله قالوا : اللهم أعطنا ما لم تعطه أحدا قبلنا ولا تعطه أحدا بعدنا فكره الله ذلك من دعائهم ،&lt;/opinions_of_scholars&gt; &lt;quran_verse&gt;( رب لو شئت أهلكتهم من قبل وإياي )&lt;/quran_verse&gt; الآية .
    &lt;/tafsir_chunk&gt;
&lt;tafsir_chunk&gt;
      وقال &lt;opinions_of_scholars&gt;السدي&lt;/opinions_of_scholars&gt; : &lt;opinions_of_scholars&gt;إن الله أمر موسى أن يأتيه في ناس من بني إسرائيل ، يعتذرون إليه من عبادة العجل ، ووعدهم موعدا ، فاختار موسى قومه سبعين رجلا على عينه ، ثم ذهب بهم ليعتذروا . فلما أتوا ذلك المكان قالوا : لن نؤمن لك يا موسى حتى نرى الله جهرة ، فإنك قد كلمته ، فأرناه . فأخذتهم الصاعقة فماتوا ، فقام موسى يبكي ويدعو الله ويقول : رب ، ماذا أقول لبني إسرائيل إذا لقيتهم وقد أهلكت خيارهم ؟&lt;/opinions_of_scholars&gt; &lt;quran_verse&gt;( رب لو شئت أهلكتهم من قبل وإياي )&lt;/quran_verse&gt;
&lt;/tafsir_chun" tabindex="0" style="content-visibility: visible; transform: translate(0px, 2470px); height: 26px;"><div class="Bl"><span>&lt;tafsir_section&gt;
&lt;tafsir_section_block&gt;
&lt;tafsir_chunk&gt;
      قال &lt;source&gt;علي بن أبي طلحة ، عن ابن عباس&lt;/source&gt; في تفسير هذه الآية : &lt;opinions_of_scholars&gt;كان الله أمره أن يختار من قومه سبعين رجلا فاختار سبعين رجلا فبرز بهم ليدعوا ربهم ، فكان فيما دعوا الله قالوا : اللهم أعطنا ما لم تعطه أحدا قبلنا ولا تعطه أحدا بعدنا فكره الله ذلك من دعائهم ،&lt;/opinions_of_scholars&gt; &lt;quran_verse&gt;( رب لو شئت أهلكتهم من قبل وإياي )&lt;/quran_verse&gt; الآية .
    &lt;/tafsir_chunk&gt;
&lt;tafsir_chunk&gt;
      وقال &lt;opinions_of_scholars&gt;السدي&lt;/opinions_of_scholars&gt; : &lt;opinions_of_scholars&gt;إن الله أمر موسى أن يأتيه في ناس من بني إسرائيل ، يعتذرون إليه من عبادة العجل ، ووعدهم موعدا ، فاختار موسى قومه سبعين رجلا على عينه ، ثم ذهب بهم ليعتذروا . فلما أتوا ذلك المكان قالوا : لن نؤمن لك يا موسى حتى نرى الله جهرة ، فإنك قد كلمته ، فأرناه . فأخذتهم الصاعقة فماتوا ، فقام موسى يبكي ويدعو الله ويقول : رب ، ماذا أقول لبني إسرائيل إذا لقيتهم وقد أهلكت خيارهم ؟&lt;/opinions_of_scholars&gt; &lt;quran_verse&gt;( رب لو شئت أهلكتهم من قبل وإياي )&lt;/quran_verse&gt;
&lt;/tafsir_chun</span></div></div><div class="l g n" title="```xml
&lt;tafsir_section&gt;
  &lt;tafsir_section_block&gt;
    &lt;tafsir_chunk&gt;
      &lt;quran_verse&gt;( واكتب لنا في هذه الدنيا حسنة وفي الآخرة )&lt;/quran_verse&gt; &lt;balagha_analysis&gt;هناك الفصل الأول من الدعاء دفع المحذور ، وهذا لتحصيل المقصود&lt;/balagha_analysis&gt;
    &lt;/tafsir_chunk&gt;
    &lt;tafsir_chunk&gt;
      &lt;quran_verse&gt;( واكتب لنا في هذه الدنيا حسنة وفي الآخرة )&lt;/quran_verse&gt; &lt;linguistic_analysis&gt;أي : أوجب لنا وأثبت لنا فيهما حسنة&lt;/linguistic_analysis&gt; ،
    &lt;/tafsir_chunk&gt;
    &lt;tafsir_chunk&gt;
      &lt;cross_references&gt;وقد تقدم تفسير ذلك في سورة البقرة . [ الآية : 201 ]&lt;/cross_references&gt;
    &lt;/tafsir_chunk&gt;
  &lt;/tafsir_section_block&gt;
  &lt;tafsir_section_block&gt;
    &lt;tafsir_chunk&gt;
      &lt;quran_verse&gt;( إنا هدنا إليك )&lt;/quran_verse&gt; &lt;linguistic_analysis&gt;أي : تبنا ورجعنا وأنبنا إليك .&lt;/linguistic_analysis&gt;
    &lt;/tafsir_chunk&gt;
    &lt;tafsir_chunk&gt;
      &lt;opinions_of_scholars&gt;قاله ابن عباس ، وسعيد بن جبير ، ومجاهد ، وأبو العالية ، والضحاك ، وإبراهيم التيمي ، والسدي ، وقتادة ، وغير واحد .&lt;/opinions_of_scholars&gt; &lt;linguistic_analysis&gt;وهو كذلك لغ" tabindex="0" style="content-visibility: visible; transform: translate(0px, 2496px); height: 26px;"><div class="Bl"><span>```xml
&lt;tafsir_section&gt;
  &lt;tafsir_section_block&gt;
    &lt;tafsir_chunk&gt;
      &lt;quran_verse&gt;( واكتب لنا في هذه الدنيا حسنة وفي الآخرة )&lt;/quran_verse&gt; &lt;balagha_analysis&gt;هناك الفصل الأول من الدعاء دفع المحذور ، وهذا لتحصيل المقصود&lt;/balagha_analysis&gt;
    &lt;/tafsir_chunk&gt;
    &lt;tafsir_chunk&gt;
      &lt;quran_verse&gt;( واكتب لنا في هذه الدنيا حسنة وفي الآخرة )&lt;/quran_verse&gt; &lt;linguistic_analysis&gt;أي : أوجب لنا وأثبت لنا فيهما حسنة&lt;/linguistic_analysis&gt; ،
    &lt;/tafsir_chunk&gt;
    &lt;tafsir_chunk&gt;
      &lt;cross_references&gt;وقد تقدم تفسير ذلك في سورة البقرة . [ الآية : 201 ]&lt;/cross_references&gt;
    &lt;/tafsir_chunk&gt;
  &lt;/tafsir_section_block&gt;
  &lt;tafsir_section_block&gt;
    &lt;tafsir_chunk&gt;
      &lt;quran_verse&gt;( إنا هدنا إليك )&lt;/quran_verse&gt; &lt;linguistic_analysis&gt;أي : تبنا ورجعنا وأنبنا إليك .&lt;/linguistic_analysis&gt;
    &lt;/tafsir_chunk&gt;
    &lt;tafsir_chunk&gt;
      &lt;opinions_of_scholars&gt;قاله ابن عباس ، وسعيد بن جبير ، ومجاهد ، وأبو العالية ، والضحاك ، وإبراهيم التيمي ، والسدي ، وقتادة ، وغير واحد .&lt;/opinions_of_scholars&gt; &lt;linguistic_analysis&gt;وهو كذلك لغ</span></div></div><div class="l Zo" title="```xml
&lt;tafsir_section&gt;
  &lt;tafsir_section_block&gt;
    &lt;tafsir_chunk&gt;
      &lt;quran_verse&gt;الذين يتبعون الرسول النبي الأمي الذي يجدونه مكتوبا عندهم في التوراة والإنجيل )&lt;/quran_verse&gt;
      &lt;opinions_of_scholars&gt;وهذه صفة محمد صلى الله عليه وسلم في كتب الأنبياء بشروا أممهم ببعثه وأمروهم بمتابعته ، ولم تزل صفاته موجودة في كتبهم يعرفها علماؤهم وأحبارهم&lt;/opinions_of_scholars&gt;
    &lt;/tafsir_chunk&gt;
  &lt;/tafsir_section_block&gt;
  &lt;tafsir_section_block&gt;
    &lt;tafsir_chunk&gt;
      &lt;source&gt;كما قال الإمام أحمد :&lt;/source&gt;
      &lt;isnad&gt;حدثنا إسماعيل ، عن الجريري ، عن أبي صخر العقيلي ، حدثني رجل من الأعراب ، قال :&lt;/isnad&gt;
      &lt;hadith&gt;جلبت جلوبة إلى المدينة في حياة رسول الله صلى الله عليه وسلم ، فلما فرغت من بيعتي قلت : لألقين هذا الرجل فلأسمعن منه ، قال : فتلقاني بين أبي بكر وعمر يمشون ، فتبعتهم في أقفائهم حتى أتوا على رجل من اليهود ناشرا التوراة يقرؤها ، يعزي بها نفسه عن ابن له في الموت كأحسن الفتيان وأجمله ، فقال رسول الله صلى الله عليه وسلم : &quot; أنشدك بالذي أنزل التوراة ، هل تجد في كتابك هذا صفتي ومخرجي ؟ &quot; فقال برأسه هكذا ، أي " tabindex="0" style="content-visibility: visible; transform: translate(0px, 2522px); height: 26px;"><div class="Bl"><span>```xml
&lt;tafsir_section&gt;
  &lt;tafsir_section_block&gt;
    &lt;tafsir_chunk&gt;
      &lt;quran_verse&gt;الذين يتبعون الرسول النبي الأمي الذي يجدونه مكتوبا عندهم في التوراة والإنجيل )&lt;/quran_verse&gt;
      &lt;opinions_of_scholars&gt;وهذه صفة محمد صلى الله عليه وسلم في كتب الأنبياء بشروا أممهم ببعثه وأمروهم بمتابعته ، ولم تزل صفاته موجودة في كتبهم يعرفها علماؤهم وأحبارهم&lt;/opinions_of_scholars&gt;
    &lt;/tafsir_chunk&gt;
  &lt;/tafsir_section_block&gt;
  &lt;tafsir_section_block&gt;
    &lt;tafsir_chunk&gt;
      &lt;source&gt;كما قال الإمام أحمد :&lt;/source&gt;
      &lt;isnad&gt;حدثنا إسماعيل ، عن الجريري ، عن أبي صخر العقيلي ، حدثني رجل من الأعراب ، قال :&lt;/isnad&gt;
      &lt;hadith&gt;جلبت جلوبة إلى المدينة في حياة رسول الله صلى الله عليه وسلم ، فلما فرغت من بيعتي قلت : لألقين هذا الرجل فلأسمعن منه ، قال : فتلقاني بين أبي بكر وعمر يمشون ، فتبعتهم في أقفائهم حتى أتوا على رجل من اليهود ناشرا التوراة يقرؤها ، يعزي بها نفسه عن ابن له في الموت كأحسن الفتيان وأجمله ، فقال رسول الله صلى الله عليه وسلم : " أنشدك بالذي أنزل التوراة ، هل تجد في كتابك هذا صفتي ومخرجي ؟ " فقال برأسه هكذا ، أي </span></div></div><div class="l" title="```xml
&lt;tafsir_section&gt;
  &lt;tafsir_section_block&gt;
    &lt;tafsir_chunk&gt;
      &lt;opinions_of_scholars&gt;
        يقول تعالى لنبيه ورسوله محمد صلى الله عليه وسلم &lt;quran_verse&gt;) قل )&lt;/quran_verse&gt; يا محمد : &lt;quran_verse&gt;( يا أيها الناس )&lt;/quran_verse&gt;
      &lt;/opinions_of_scholars&gt;
      &lt;general_vs_specific&gt;وهذا خطاب للأحمر والأسود ، والعربي والعجمي ،&lt;/general_vs_specific&gt;
      &lt;quran_verse&gt;( إني رسول الله إليكم جميعا )&lt;/quran_verse&gt;
      &lt;opinions_of_scholars&gt;أي : جميعكم ،&lt;/opinions_of_scholars&gt;
      &lt;theological_points&gt;وهذا من شرفه وعظمته أنه خاتم النبيين ، وأنه مبعوث إلى الناس كافة ،&lt;/theological_points&gt;
      &lt;cross_references&gt;
        كما قال تعالى : &lt;quran_verse&gt;( قل الله شهيد بيني وبينكم وأوحي إلي هذا القرآن لأنذركم به ومن بلغ )&lt;/quran_verse&gt; [ الأنعام : 19 ] وقال تعالى : &lt;quran_verse&gt;( ومن يكفر به من الأحزاب فالنار موعده )&lt;/quran_verse&gt; [ هود : 17 ] وقال تعالى : &lt;quran_verse&gt;( وقل للذين أوتوا الكتاب والأميين أأسلمتم فإن أسلموا فقد اهتدوا وإن تولوا فإنما عليك البلاغ )&lt;/quran_verse&gt; [ آل عمران : 20 ] والآيات ف" tabindex="0" style="content-visibility: visible; transform: translate(0px, 2548px); height: 26px;"><div class="Bl"><span>```xml
&lt;tafsir_section&gt;
  &lt;tafsir_section_block&gt;
    &lt;tafsir_chunk&gt;
      &lt;opinions_of_scholars&gt;
        يقول تعالى لنبيه ورسوله محمد صلى الله عليه وسلم &lt;quran_verse&gt;) قل )&lt;/quran_verse&gt; يا محمد : &lt;quran_verse&gt;( يا أيها الناس )&lt;/quran_verse&gt;
      &lt;/opinions_of_scholars&gt;
      &lt;general_vs_specific&gt;وهذا خطاب للأحمر والأسود ، والعربي والعجمي ،&lt;/general_vs_specific&gt;
      &lt;quran_verse&gt;( إني رسول الله إليكم جميعا )&lt;/quran_verse&gt;
      &lt;opinions_of_scholars&gt;أي : جميعكم ،&lt;/opinions_of_scholars&gt;
      &lt;theological_points&gt;وهذا من شرفه وعظمته أنه خاتم النبيين ، وأنه مبعوث إلى الناس كافة ،&lt;/theological_points&gt;
      &lt;cross_references&gt;
        كما قال تعالى : &lt;quran_verse&gt;( قل الله شهيد بيني وبينكم وأوحي إلي هذا القرآن لأنذركم به ومن بلغ )&lt;/quran_verse&gt; [ الأنعام : 19 ] وقال تعالى : &lt;quran_verse&gt;( ومن يكفر به من الأحزاب فالنار موعده )&lt;/quran_verse&gt; [ هود : 17 ] وقال تعالى : &lt;quran_verse&gt;( وقل للذين أوتوا الكتاب والأميين أأسلمتم فإن أسلموا فقد اهتدوا وإن تولوا فإنما عليك البلاغ )&lt;/quran_verse&gt; [ آل عمران : 20 ] والآيات ف</span></div></div><div class="l Zo" title="```xml
&lt;tafsir_section&gt;
  &lt;tafsir_section_block&gt;
    &lt;tafsir_chunk&gt;
      &lt;opinions_of_scholars&gt;يقول تعالى مخبرا عن بني إسرائيل أن منهم طائفة يتبعون الحق ويعدلون به&lt;/opinions_of_scholars&gt; ، كما قال تعالى : &lt;cross_references&gt;&lt;quran_verse&gt;( من أهل الكتاب أمة قائمة يتلون آيات الله آناء الليل وهم يسجدون )&lt;/quran_verse&gt;&lt;/cross_references&gt; [ آل عمران : 113 ] ،
    &lt;/tafsir_chunk&gt;
    &lt;tafsir_chunk&gt;
      وقال تعالى : &lt;cross_references&gt;&lt;quran_verse&gt;( وإن من أهل الكتاب لمن يؤمن بالله وما أنزل إليكم وما أنزل إليهم خاشعين لله لا يشترون بآيات الله ثمنا قليلا أولئك لهم أجرهم عند ربهم إن الله سريع الحساب )&lt;/quran_verse&gt;&lt;/cross_references&gt; [ آل عمران : 199 ] ،
    &lt;/tafsir_chunk&gt;
    &lt;tafsir_chunk&gt;
      وقال تعالى : &lt;cross_references&gt;&lt;quran_verse&gt;( الذين آتيناهم الكتاب من قبله هم به يؤمنون وإذا يتلى عليهم قالوا آمنا به إنه الحق من ربنا إنا كنا من قبله مسلمين أولئك يؤتون أجرهم مرتين بما صبروا [ ويدرءون بالحسنة السيئة ومما رزقناهم ينفقون ] )&lt;/quran_verse&gt;&lt;/cross_references&gt; [ القصص : 52 - 54 ] ،
    &lt;/tafsir_chunk&gt;
    &lt;taf" tabindex="0" style="content-visibility: visible; transform: translate(0px, 2574px); height: 26px;"><div class="Bl"><span>```xml
&lt;tafsir_section&gt;
  &lt;tafsir_section_block&gt;
    &lt;tafsir_chunk&gt;
      &lt;opinions_of_scholars&gt;يقول تعالى مخبرا عن بني إسرائيل أن منهم طائفة يتبعون الحق ويعدلون به&lt;/opinions_of_scholars&gt; ، كما قال تعالى : &lt;cross_references&gt;&lt;quran_verse&gt;( من أهل الكتاب أمة قائمة يتلون آيات الله آناء الليل وهم يسجدون )&lt;/quran_verse&gt;&lt;/cross_references&gt; [ آل عمران : 113 ] ،
    &lt;/tafsir_chunk&gt;
    &lt;tafsir_chunk&gt;
      وقال تعالى : &lt;cross_references&gt;&lt;quran_verse&gt;( وإن من أهل الكتاب لمن يؤمن بالله وما أنزل إليكم وما أنزل إليهم خاشعين لله لا يشترون بآيات الله ثمنا قليلا أولئك لهم أجرهم عند ربهم إن الله سريع الحساب )&lt;/quran_verse&gt;&lt;/cross_references&gt; [ آل عمران : 199 ] ،
    &lt;/tafsir_chunk&gt;
    &lt;tafsir_chunk&gt;
      وقال تعالى : &lt;cross_references&gt;&lt;quran_verse&gt;( الذين آتيناهم الكتاب من قبله هم به يؤمنون وإذا يتلى عليهم قالوا آمنا به إنه الحق من ربنا إنا كنا من قبله مسلمين أولئك يؤتون أجرهم مرتين بما صبروا [ ويدرءون بالحسنة السيئة ومما رزقناهم ينفقون ] )&lt;/quran_verse&gt;&lt;/cross_references&gt; [ القصص : 52 - 54 ] ،
    &lt;/tafsir_chunk&gt;
    &lt;taf</span></div></div><div class="l" title="```xml
&lt;tafsir_section&gt;
  &lt;tafsir_section_block&gt;
    &lt;tafsir_chunk&gt;
      يقول تعالى &lt;quran_verse&gt;واذكروا نعمتي عليكم في إجابتي لنبيكم موسى عليه السلام حين استسقاني لكم وتيسيري لكم الماء وإخراجه لكم من حجر يحمل معكم وتفجيري الماء لكم منه من ثنتي عشرة عينا كل سبط من أسباطكم عين قد عرفوها فكلو من المن والسلوى واشربوا من هذا الماء الذي أنبعته لكم بلا سعي منكم ولا كد واعبدوا الذي سخر لكم ذلك &quot;ولا تعثوا في الأرض مفسدين&quot;&lt;/quran_verse&gt; &lt;command_and_prohibition&gt;ولا تقابلوا النعم بالعصيان فتسلبوها&lt;/command_and_prohibition&gt;.
    &lt;/tafsir_chunk&gt;
  &lt;/tafsir_section_block&gt;
  &lt;tafsir_section_block&gt;
    &lt;tafsir_chunk&gt;
      &lt;opinions_of_scholars&gt;وقد بسطه المفسرون في كلامهم كما قال: ابن عباس رضي الله عنه وجعل بين ظهرانيهم حجر مربع وأمر موسى عليه السلام فضربه بعصاه فانفجرت منه اثنتا عشرة عينا في كل ناحية منه ثلاث عيون وأعلم كل سبط عينهم يشربون منها لا يرتحلون من منقلة إلا وجدوا ذلك معهم بالمكان الذي كان منهم بالمنزل الأول&lt;/opinions_of_scholars&gt; وهذا قطعة من الحديث الذي رواه &lt;source&gt;النسائي&lt;/source&gt; و&lt;source&gt;ابن جرير&lt;/source&gt; " tabindex="0" style="content-visibility: visible; transform: translate(0px, 2600px); height: 26px;"><div class="Bl"><span>```xml
&lt;tafsir_section&gt;
  &lt;tafsir_section_block&gt;
    &lt;tafsir_chunk&gt;
      يقول تعالى &lt;quran_verse&gt;واذكروا نعمتي عليكم في إجابتي لنبيكم موسى عليه السلام حين استسقاني لكم وتيسيري لكم الماء وإخراجه لكم من حجر يحمل معكم وتفجيري الماء لكم منه من ثنتي عشرة عينا كل سبط من أسباطكم عين قد عرفوها فكلو من المن والسلوى واشربوا من هذا الماء الذي أنبعته لكم بلا سعي منكم ولا كد واعبدوا الذي سخر لكم ذلك "ولا تعثوا في الأرض مفسدين"&lt;/quran_verse&gt; &lt;command_and_prohibition&gt;ولا تقابلوا النعم بالعصيان فتسلبوها&lt;/command_and_prohibition&gt;.
    &lt;/tafsir_chunk&gt;
  &lt;/tafsir_section_block&gt;
  &lt;tafsir_section_block&gt;
    &lt;tafsir_chunk&gt;
      &lt;opinions_of_scholars&gt;وقد بسطه المفسرون في كلامهم كما قال: ابن عباس رضي الله عنه وجعل بين ظهرانيهم حجر مربع وأمر موسى عليه السلام فضربه بعصاه فانفجرت منه اثنتا عشرة عينا في كل ناحية منه ثلاث عيون وأعلم كل سبط عينهم يشربون منها لا يرتحلون من منقلة إلا وجدوا ذلك معهم بالمكان الذي كان منهم بالمنزل الأول&lt;/opinions_of_scholars&gt; وهذا قطعة من الحديث الذي رواه &lt;source&gt;النسائي&lt;/source&gt; و&lt;source&gt;ابن جرير&lt;/source&gt; </span></div></div><div class="l Zo" title="```xml
&lt;tafsir_section&gt;
  &lt;tafsir_section_block&gt;
    &lt;tafsir_chunk&gt;
      &lt;historical_context&gt;يقول تعالى لائما لهم على نكولهم عن الجهاد ودخولهم الأرض المقدسة لما قدموا من برد مصر صحبة موسى عليه السلام فأمروا بدخول الأرض المقدسة التي هي ميراث لهم عن أبيهم إسرائيل وقتال من فيها من العماليق الكفرة فنكلوا عن قتالهم وضعفوا واستحسروا فرماهم الله في التيه عقوبة لهم&lt;/historical_context&gt;
      &lt;cross_references&gt;كما ذكره تعالى في سورة المائدة&lt;/cross_references&gt;
    &lt;/tafsir_chunk&gt;
    &lt;tafsir_chunk&gt;
      &lt;argument&gt;ولهذا كان أصح القولين أن هذه البلدة هي بيت المقدس&lt;/argument&gt;
      &lt;opinions_of_scholars&gt;كما نص على ذلك &lt;source&gt;السدي&lt;/source&gt; و&lt;source&gt;الربيع بن أنس&lt;/source&gt; و&lt;source&gt;قتادة&lt;/source&gt; و&lt;source&gt;أبو مسلم الأصفهاني&lt;/source&gt; وغير واحد&lt;/opinions_of_scholars&gt;
      &lt;quran_verse&gt;وقد قال الله تعالى حاكيا عن موسى &quot;يا قوم ادخلوا الأرض المقدسة التي كتب الله لكم ولا ترتدوا&quot; الآيات.&lt;/quran_verse&gt;
    &lt;/tafsir_chunk&gt;
    &lt;tafsir_chunk&gt;
      &lt;opinions_of_scholars&gt;وقال: آخرون هي أريحا ويحكى عن &lt;source&gt;ابن عباس&lt;/source&gt; و&lt;so" tabindex="0" style="content-visibility: visible; transform: translate(0px, 2626px); height: 26px;"><div class="Bl"><span>```xml
&lt;tafsir_section&gt;
  &lt;tafsir_section_block&gt;
    &lt;tafsir_chunk&gt;
      &lt;historical_context&gt;يقول تعالى لائما لهم على نكولهم عن الجهاد ودخولهم الأرض المقدسة لما قدموا من برد مصر صحبة موسى عليه السلام فأمروا بدخول الأرض المقدسة التي هي ميراث لهم عن أبيهم إسرائيل وقتال من فيها من العماليق الكفرة فنكلوا عن قتالهم وضعفوا واستحسروا فرماهم الله في التيه عقوبة لهم&lt;/historical_context&gt;
      &lt;cross_references&gt;كما ذكره تعالى في سورة المائدة&lt;/cross_references&gt;
    &lt;/tafsir_chunk&gt;
    &lt;tafsir_chunk&gt;
      &lt;argument&gt;ولهذا كان أصح القولين أن هذه البلدة هي بيت المقدس&lt;/argument&gt;
      &lt;opinions_of_scholars&gt;كما نص على ذلك &lt;source&gt;السدي&lt;/source&gt; و&lt;source&gt;الربيع بن أنس&lt;/source&gt; و&lt;source&gt;قتادة&lt;/source&gt; و&lt;source&gt;أبو مسلم الأصفهاني&lt;/source&gt; وغير واحد&lt;/opinions_of_scholars&gt;
      &lt;quran_verse&gt;وقد قال الله تعالى حاكيا عن موسى "يا قوم ادخلوا الأرض المقدسة التي كتب الله لكم ولا ترتدوا" الآيات.&lt;/quran_verse&gt;
    &lt;/tafsir_chunk&gt;
    &lt;tafsir_chunk&gt;
      &lt;opinions_of_scholars&gt;وقال: آخرون هي أريحا ويحكى عن &lt;source&gt;ابن عباس&lt;/source&gt; و&lt;so</span></div></div><div class="l" title="```xml
&lt;tafsir_section&gt;
  &lt;tafsir_section_block&gt;
    &lt;tafsir_chunk&gt;
      وقوله تعالى &lt;quran_verse&gt;فبدل الذين ظلموا قولا غير الذي قيل لهم&lt;/quran_verse&gt;
    &lt;/tafsir_chunk&gt;
    &lt;tafsir_chunk&gt;
      &lt;source&gt;قال: البخاري&lt;/source&gt; &lt;isnad&gt;حدثني محمد حدثنا عبدالرحمن بن مهدي عن ابن المبارك عن معمر عن همام بن منبه عن أبي هريرة رضي الله عنه عن النبي صلى الله عليه وسلم&lt;/isnad&gt; قال &lt;hadith&gt;&quot;قيل لبني إسرائيل: &lt;quran_verse&gt;ادخلوا الباب سجدا وقولوا حطة&lt;/quran_verse&gt; - فدخلوا يزحفون على استاهم فبدلوا وقالوا حبة في شعرة&quot;&lt;/hadith&gt;
    &lt;/tafsir_chunk&gt;
  &lt;/tafsir_section_block&gt;
  &lt;tafsir_section_block&gt;
    &lt;tafsir_chunk&gt;
      &lt;source&gt;ورواه النسائي&lt;/source&gt; &lt;isnad&gt;عن محمد بن إسماعيل بن إبراهيم عن عبدالرحمن به&lt;/isnad&gt; موقوفا وعن &lt;isnad&gt;محمد بن عبيد بن محمد عن ابن المبارك ببعضه&lt;/isnad&gt; مسندا في قوله تعالى &lt;quran_verse&gt;&quot;حطة&quot;&lt;/quran_verse&gt; قال &lt;hadith&gt;فبدلوا وقالوا حبة&lt;/hadith&gt;
    &lt;/tafsir_chunk&gt;
    &lt;tafsir_chunk&gt;
      &lt;source&gt;وقال عبدالرزاق&lt;/source&gt; &lt;isnad&gt;أنبأنا معمر عن همام بن منبه أنه سمع أبا هريرة يقول قال رسول الله صلى الل" tabindex="0" style="content-visibility: visible; transform: translate(0px, 2652px); height: 26px;"><div class="Bl"><span>```xml
&lt;tafsir_section&gt;
  &lt;tafsir_section_block&gt;
    &lt;tafsir_chunk&gt;
      وقوله تعالى &lt;quran_verse&gt;فبدل الذين ظلموا قولا غير الذي قيل لهم&lt;/quran_verse&gt;
    &lt;/tafsir_chunk&gt;
    &lt;tafsir_chunk&gt;
      &lt;source&gt;قال: البخاري&lt;/source&gt; &lt;isnad&gt;حدثني محمد حدثنا عبدالرحمن بن مهدي عن ابن المبارك عن معمر عن همام بن منبه عن أبي هريرة رضي الله عنه عن النبي صلى الله عليه وسلم&lt;/isnad&gt; قال &lt;hadith&gt;"قيل لبني إسرائيل: &lt;quran_verse&gt;ادخلوا الباب سجدا وقولوا حطة&lt;/quran_verse&gt; - فدخلوا يزحفون على استاهم فبدلوا وقالوا حبة في شعرة"&lt;/hadith&gt;
    &lt;/tafsir_chunk&gt;
  &lt;/tafsir_section_block&gt;
  &lt;tafsir_section_block&gt;
    &lt;tafsir_chunk&gt;
      &lt;source&gt;ورواه النسائي&lt;/source&gt; &lt;isnad&gt;عن محمد بن إسماعيل بن إبراهيم عن عبدالرحمن به&lt;/isnad&gt; موقوفا وعن &lt;isnad&gt;محمد بن عبيد بن محمد عن ابن المبارك ببعضه&lt;/isnad&gt; مسندا في قوله تعالى &lt;quran_verse&gt;"حطة"&lt;/quran_verse&gt; قال &lt;hadith&gt;فبدلوا وقالوا حبة&lt;/hadith&gt;
    &lt;/tafsir_chunk&gt;
    &lt;tafsir_chunk&gt;
      &lt;source&gt;وقال عبدالرزاق&lt;/source&gt; &lt;isnad&gt;أنبأنا معمر عن همام بن منبه أنه سمع أبا هريرة يقول قال رسول الله صلى الل</span></div></div><div class="l Zo" title="```xml
&lt;tafsir_section&gt;
  &lt;tafsir_section_block&gt;
    &lt;tafsir_chunk&gt;
      &lt;cross_references&gt;هذا السياق هو بسط لقوله تعالى : &lt;quran_verse&gt;( ولقد علمتم الذين اعتدوا منكم في السبت فقلنا لهم كونوا قردة خاسئين )&lt;/quran_verse&gt; [ البقرة : 65 ]&lt;/cross_references&gt;
    &lt;/tafsir_chunk&gt;
  &lt;/tafsir_section_block&gt;
  &lt;tafsir_section_block&gt;
    &lt;tafsir_chunk&gt;
      &lt;opinions_of_scholars&gt;يقول [ الله ] تعالى ، لنبيه صلوات الله وسلامه عليه : &lt;quran_verse&gt;( واسألهم )&lt;/quran_verse&gt; أي : واسأل هؤلاء اليهود الذين بحضرتك عن قصة أصحابهم الذين خالفوا أمر الله ، ففاجأتهم نقمته على صنيعهم واعتدائهم واحتيالهم في المخالفة ، وحذر هؤلاء من كتمان صفتك التي يجدونها في كتبهم ; لئلا يحل بهم ما حل بإخوانهم وسلفهم .&lt;/opinions_of_scholars&gt;
    &lt;/tafsir_chunk&gt;
  &lt;/tafsir_section_block&gt;
  &lt;tafsir_section_block&gt;
    &lt;tafsir_chunk&gt;
      &lt;historical_context&gt;وهذه القرية هي &quot; أيلة &quot; وهي على شاطئ بحر القلزم .&lt;/historical_context&gt;
    &lt;/tafsir_chunk&gt;
    &lt;tafsir_chunk&gt;
      &lt;source&gt;قال محمد بن إسحاق :&lt;/source&gt;
      &lt;isnad&gt;عن داود بن الحصين ، عن عكرمة عن" tabindex="0" style="content-visibility: visible; transform: translate(0px, 2678px); height: 26px;"><div class="Bl"><span>```xml
&lt;tafsir_section&gt;
  &lt;tafsir_section_block&gt;
    &lt;tafsir_chunk&gt;
      &lt;cross_references&gt;هذا السياق هو بسط لقوله تعالى : &lt;quran_verse&gt;( ولقد علمتم الذين اعتدوا منكم في السبت فقلنا لهم كونوا قردة خاسئين )&lt;/quran_verse&gt; [ البقرة : 65 ]&lt;/cross_references&gt;
    &lt;/tafsir_chunk&gt;
  &lt;/tafsir_section_block&gt;
  &lt;tafsir_section_block&gt;
    &lt;tafsir_chunk&gt;
      &lt;opinions_of_scholars&gt;يقول [ الله ] تعالى ، لنبيه صلوات الله وسلامه عليه : &lt;quran_verse&gt;( واسألهم )&lt;/quran_verse&gt; أي : واسأل هؤلاء اليهود الذين بحضرتك عن قصة أصحابهم الذين خالفوا أمر الله ، ففاجأتهم نقمته على صنيعهم واعتدائهم واحتيالهم في المخالفة ، وحذر هؤلاء من كتمان صفتك التي يجدونها في كتبهم ; لئلا يحل بهم ما حل بإخوانهم وسلفهم .&lt;/opinions_of_scholars&gt;
    &lt;/tafsir_chunk&gt;
  &lt;/tafsir_section_block&gt;
  &lt;tafsir_section_block&gt;
    &lt;tafsir_chunk&gt;
      &lt;historical_context&gt;وهذه القرية هي " أيلة " وهي على شاطئ بحر القلزم .&lt;/historical_context&gt;
    &lt;/tafsir_chunk&gt;
    &lt;tafsir_chunk&gt;
      &lt;source&gt;قال محمد بن إسحاق :&lt;/source&gt;
      &lt;isnad&gt;عن داود بن الحصين ، عن عكرمة عن</span></div></div><div class="l" title="```xml
&lt;tafsir_section&gt;
  &lt;tafsir_section_block&gt;
    &lt;tafsir_chunk&gt;
      &lt;summary&gt;خبر تعالى عن أهل هذه القرية أنهم صاروا إلى ثلاث فرق : فرقة ارتكبت المحذور ، واحتالوا على اصطياد السمك يوم السبت ،&lt;/summary&gt;
    &lt;/tafsir_chunk&gt;
    &lt;tafsir_chunk&gt;
      &lt;cross_references&gt;كما تقدم بيانه في سورة البقرة .&lt;/cross_references&gt;
    &lt;/tafsir_chunk&gt;
  &lt;/tafsir_section_block&gt;
  &lt;tafsir_section_block&gt;
    &lt;tafsir_chunk&gt;
      وفرقة نهت عن ذلك ، [ وأنكرت ] واعتزلتهم . وفرقة سكتت فلم تفعل ولم تنه ،
    &lt;/tafsir_chunk&gt;
    &lt;tafsir_chunk&gt;
      ولكنها قالت للمنكرة : &lt;quran_verse&gt;( لم تعظون قوما الله مهلكهم أو معذبهم عذابا شديدا )&lt;/quran_verse&gt; ؟
    &lt;/tafsir_chunk&gt;
    &lt;tafsir_chunk&gt;
      &lt;opinions_of_scholars&gt;أي : لم تنهون هؤلاء ، وقد علمتم أنهم هلكوا واستحقوا العقوبة من الله ؟ فلا فائدة في نهيكم إياهم .&lt;/opinions_of_scholars&gt;
    &lt;/tafsir_chunk&gt;
  &lt;/tafsir_section_block&gt;
  &lt;tafsir_section_block&gt;
    &lt;tafsir_chunk&gt;
      قالت لهم المنكرة : &lt;quran_verse&gt;( معذرة إلى ربكم )&lt;/quran_verse&gt;
    &lt;/tafsir_chunk&gt;
    &lt;tafsir_chunk&gt;
" tabindex="0" style="content-visibility: visible; transform: translate(0px, 2704px); height: 26px;"><div class="Bl"><span>```xml
&lt;tafsir_section&gt;
  &lt;tafsir_section_block&gt;
    &lt;tafsir_chunk&gt;
      &lt;summary&gt;خبر تعالى عن أهل هذه القرية أنهم صاروا إلى ثلاث فرق : فرقة ارتكبت المحذور ، واحتالوا على اصطياد السمك يوم السبت ،&lt;/summary&gt;
    &lt;/tafsir_chunk&gt;
    &lt;tafsir_chunk&gt;
      &lt;cross_references&gt;كما تقدم بيانه في سورة البقرة .&lt;/cross_references&gt;
    &lt;/tafsir_chunk&gt;
  &lt;/tafsir_section_block&gt;
  &lt;tafsir_section_block&gt;
    &lt;tafsir_chunk&gt;
      وفرقة نهت عن ذلك ، [ وأنكرت ] واعتزلتهم . وفرقة سكتت فلم تفعل ولم تنه ،
    &lt;/tafsir_chunk&gt;
    &lt;tafsir_chunk&gt;
      ولكنها قالت للمنكرة : &lt;quran_verse&gt;( لم تعظون قوما الله مهلكهم أو معذبهم عذابا شديدا )&lt;/quran_verse&gt; ؟
    &lt;/tafsir_chunk&gt;
    &lt;tafsir_chunk&gt;
      &lt;opinions_of_scholars&gt;أي : لم تنهون هؤلاء ، وقد علمتم أنهم هلكوا واستحقوا العقوبة من الله ؟ فلا فائدة في نهيكم إياهم .&lt;/opinions_of_scholars&gt;
    &lt;/tafsir_chunk&gt;
  &lt;/tafsir_section_block&gt;
  &lt;tafsir_section_block&gt;
    &lt;tafsir_chunk&gt;
      قالت لهم المنكرة : &lt;quran_verse&gt;( معذرة إلى ربكم )&lt;/quran_verse&gt;
    &lt;/tafsir_chunk&gt;
    &lt;tafsir_chunk&gt;
</span></div></div><div class="l Zo" title="```xml
&lt;tafsir_section&gt;
  &lt;tafsir_section_block&gt;
    &lt;tafsir_chunk&gt;
      قال تعالى : &lt;quran_verse&gt;فلما نسوا ما ذكروا به&lt;/quran_verse&gt;
    &lt;/tafsir_chunk&gt;
    &lt;tafsir_chunk&gt;
      &lt;opinions_of_scholars&gt;أي : فلما أبى الفاعلون المنكر قبول النصيحة ،&lt;/opinions_of_scholars&gt;
    &lt;/tafsir_chunk&gt;
    &lt;tafsir_chunk&gt;
      &lt;quran_verse&gt;أنجينا الذين ينهون عن السوء وأخذنا الذين ظلموا&lt;/quran_verse&gt;
      &lt;opinions_of_scholars&gt;أي : ارتكبوا المعصية&lt;/opinions_of_scholars&gt;
    &lt;/tafsir_chunk&gt;
    &lt;tafsir_chunk&gt;
      &lt;quran_verse&gt;بعذاب بئيس&lt;/quran_verse&gt;
    &lt;/tafsir_chunk&gt;
    &lt;tafsir_chunk&gt;
      &lt;opinions_of_scholars&gt;
        فنص على نجاة الناهين وهلاك الظالمين ، وسكت عن الساكتين ; لأن الجزاء من جنس العمل ، فهم لا يستحقون مدحا فيمدحوا ، ولا ارتكبوا عظيما فيذموا ، ومع هذا فقد اختلف الأئمة فيهم : هل كانوا من الهالكين أو من الناجين ؟ على قولين :
      &lt;/opinions_of_scholars&gt;
    &lt;/tafsir_chunk&gt;
  &lt;/tafsir_section_block&gt;
  &lt;tafsir_section_block&gt;
    &lt;tafsir_chunk&gt;
      &lt;isnad&gt;قال علي بن أبي طلحة ، عن ابن عباس :&lt;/isnad&gt;
    &lt;/" tabindex="0" style="content-visibility: visible; transform: translate(0px, 2730px); height: 26px;"><div class="Bl"><span>```xml
&lt;tafsir_section&gt;
  &lt;tafsir_section_block&gt;
    &lt;tafsir_chunk&gt;
      قال تعالى : &lt;quran_verse&gt;فلما نسوا ما ذكروا به&lt;/quran_verse&gt;
    &lt;/tafsir_chunk&gt;
    &lt;tafsir_chunk&gt;
      &lt;opinions_of_scholars&gt;أي : فلما أبى الفاعلون المنكر قبول النصيحة ،&lt;/opinions_of_scholars&gt;
    &lt;/tafsir_chunk&gt;
    &lt;tafsir_chunk&gt;
      &lt;quran_verse&gt;أنجينا الذين ينهون عن السوء وأخذنا الذين ظلموا&lt;/quran_verse&gt;
      &lt;opinions_of_scholars&gt;أي : ارتكبوا المعصية&lt;/opinions_of_scholars&gt;
    &lt;/tafsir_chunk&gt;
    &lt;tafsir_chunk&gt;
      &lt;quran_verse&gt;بعذاب بئيس&lt;/quran_verse&gt;
    &lt;/tafsir_chunk&gt;
    &lt;tafsir_chunk&gt;
      &lt;opinions_of_scholars&gt;
        فنص على نجاة الناهين وهلاك الظالمين ، وسكت عن الساكتين ; لأن الجزاء من جنس العمل ، فهم لا يستحقون مدحا فيمدحوا ، ولا ارتكبوا عظيما فيذموا ، ومع هذا فقد اختلف الأئمة فيهم : هل كانوا من الهالكين أو من الناجين ؟ على قولين :
      &lt;/opinions_of_scholars&gt;
    &lt;/tafsir_chunk&gt;
  &lt;/tafsir_section_block&gt;
  &lt;tafsir_section_block&gt;
    &lt;tafsir_chunk&gt;
      &lt;isnad&gt;قال علي بن أبي طلحة ، عن ابن عباس :&lt;/isnad&gt;
    &lt;/</span></div></div><div class="l" title="```xml
&lt;tafsir_section&gt;
  &lt;tafsir_section_block&gt;
    &lt;tafsir_chunk&gt;
      قال تعالى : &lt;quran_verse&gt;فلما نسوا ما ذكروا به&lt;/quran_verse&gt; أي : &lt;opinions_of_scholars&gt;فلما أبى الفاعلون المنكر قبول النصيحة&lt;/opinions_of_scholars&gt; ، &lt;quran_verse&gt;أنجينا الذين ينهون عن السوء وأخذنا الذين ظلموا&lt;/quran_verse&gt; أي : &lt;opinions_of_scholars&gt;ارتكبوا المعصية&lt;/opinions_of_scholars&gt; &lt;quran_verse&gt;بعذاب بئيس&lt;/quran_verse&gt; &lt;opinions_of_scholars&gt;فنص على نجاة الناهين وهلاك الظالمين ، وسكت عن الساكتين ; لأن الجزاء من جنس العمل ، فهم لا يستحقون مدحا فيمدحوا ، ولا ارتكبوا عظيما فيذموا&lt;/opinions_of_scholars&gt; ، ومع هذا فقد &lt;variant_interpretations&gt;اختلف الأئمة فيهم : هل كانوا من الهالكين أو من الناجين ؟ على قولين&lt;/variant_interpretations&gt; :
    &lt;/tafsir_chunk&gt;
  &lt;/tafsir_section_block&gt;
  &lt;tafsir_section_block&gt;
    &lt;tafsir_chunk&gt;
      &lt;isnad&gt;قال علي بن أبي طلحة ، عن ابن عباس&lt;/isnad&gt; : &lt;quran_verse&gt;وإذ قالت أمة منهم لم تعظون قوما الله مهلكهم أو معذبهم عذابا شديدا&lt;/quran_verse&gt; [ قال : ] &lt;hadith&gt;&lt;historical_context&gt;هي قرية على شاطئ البحر بين" tabindex="0" style="content-visibility: visible; transform: translate(0px, 2756px); height: 26px;"><div class="Bl"><span>```xml
&lt;tafsir_section&gt;
  &lt;tafsir_section_block&gt;
    &lt;tafsir_chunk&gt;
      قال تعالى : &lt;quran_verse&gt;فلما نسوا ما ذكروا به&lt;/quran_verse&gt; أي : &lt;opinions_of_scholars&gt;فلما أبى الفاعلون المنكر قبول النصيحة&lt;/opinions_of_scholars&gt; ، &lt;quran_verse&gt;أنجينا الذين ينهون عن السوء وأخذنا الذين ظلموا&lt;/quran_verse&gt; أي : &lt;opinions_of_scholars&gt;ارتكبوا المعصية&lt;/opinions_of_scholars&gt; &lt;quran_verse&gt;بعذاب بئيس&lt;/quran_verse&gt; &lt;opinions_of_scholars&gt;فنص على نجاة الناهين وهلاك الظالمين ، وسكت عن الساكتين ; لأن الجزاء من جنس العمل ، فهم لا يستحقون مدحا فيمدحوا ، ولا ارتكبوا عظيما فيذموا&lt;/opinions_of_scholars&gt; ، ومع هذا فقد &lt;variant_interpretations&gt;اختلف الأئمة فيهم : هل كانوا من الهالكين أو من الناجين ؟ على قولين&lt;/variant_interpretations&gt; :
    &lt;/tafsir_chunk&gt;
  &lt;/tafsir_section_block&gt;
  &lt;tafsir_section_block&gt;
    &lt;tafsir_chunk&gt;
      &lt;isnad&gt;قال علي بن أبي طلحة ، عن ابن عباس&lt;/isnad&gt; : &lt;quran_verse&gt;وإذ قالت أمة منهم لم تعظون قوما الله مهلكهم أو معذبهم عذابا شديدا&lt;/quran_verse&gt; [ قال : ] &lt;hadith&gt;&lt;historical_context&gt;هي قرية على شاطئ البحر بين</span></div></div><div class="l Zo" title="```xml
&lt;tafsir_section&gt;
  &lt;tafsir_section_block&gt;
    &lt;tafsir_chunk&gt;
      &lt;quran_verse&gt;( تأذن )&lt;/quran_verse&gt;
      &lt;linguistic_analysis&gt;تفعل من الإذن أي : أعلم&lt;/linguistic_analysis&gt;
      &lt;tafsir_chunk&gt; ، &lt;/tafsir_chunk&gt;
      &lt;opinions_of_scholars&gt;قاله مجاهد .&lt;/opinions_of_scholars&gt;
      &lt;opinions_of_scholars&gt;وقال غيره : أمر .&lt;/opinions_of_scholars&gt;
    &lt;/tafsir_chunk&gt;
  &lt;/tafsir_section_block&gt;
  &lt;tafsir_section_block&gt;
    &lt;tafsir_chunk&gt;
      &lt;grammatical_parsing&gt;وفي قوة الكلام ما يفيد معنى القسم من هذه اللفظة ، ولهذا تلقيت باللام في قوله :&lt;/grammatical_parsing&gt;
      &lt;quran_verse&gt;( ليبعثن عليهم )&lt;/quran_verse&gt;
      &lt;tafsir_chunk&gt;أي : على اليهود&lt;/tafsir_chunk&gt;
    &lt;/tafsir_chunk&gt;
    &lt;tafsir_chunk&gt;
      &lt;quran_verse&gt;( إلى يوم القيامة من يسومهم سوء العذاب )&lt;/quran_verse&gt;
      &lt;tafsir_chunk&gt;أي : بسبب عصيانهم ومخالفتهم أوامر الله وشرعه واحتيالهم على المحارم .&lt;/tafsir_chunk&gt;
    &lt;/tafsir_chunk&gt;
  &lt;/tafsir_section_block&gt;
  &lt;tafsir_section_block&gt;
    &lt;tafsir_chunk&gt;
      &lt;historical_context&gt;ويقال : إن موسى ،" tabindex="0" style="content-visibility: visible; transform: translate(0px, 2782px); height: 26px;"><div class="Bl"><span>```xml
&lt;tafsir_section&gt;
  &lt;tafsir_section_block&gt;
    &lt;tafsir_chunk&gt;
      &lt;quran_verse&gt;( تأذن )&lt;/quran_verse&gt;
      &lt;linguistic_analysis&gt;تفعل من الإذن أي : أعلم&lt;/linguistic_analysis&gt;
      &lt;tafsir_chunk&gt; ، &lt;/tafsir_chunk&gt;
      &lt;opinions_of_scholars&gt;قاله مجاهد .&lt;/opinions_of_scholars&gt;
      &lt;opinions_of_scholars&gt;وقال غيره : أمر .&lt;/opinions_of_scholars&gt;
    &lt;/tafsir_chunk&gt;
  &lt;/tafsir_section_block&gt;
  &lt;tafsir_section_block&gt;
    &lt;tafsir_chunk&gt;
      &lt;grammatical_parsing&gt;وفي قوة الكلام ما يفيد معنى القسم من هذه اللفظة ، ولهذا تلقيت باللام في قوله :&lt;/grammatical_parsing&gt;
      &lt;quran_verse&gt;( ليبعثن عليهم )&lt;/quran_verse&gt;
      &lt;tafsir_chunk&gt;أي : على اليهود&lt;/tafsir_chunk&gt;
    &lt;/tafsir_chunk&gt;
    &lt;tafsir_chunk&gt;
      &lt;quran_verse&gt;( إلى يوم القيامة من يسومهم سوء العذاب )&lt;/quran_verse&gt;
      &lt;tafsir_chunk&gt;أي : بسبب عصيانهم ومخالفتهم أوامر الله وشرعه واحتيالهم على المحارم .&lt;/tafsir_chunk&gt;
    &lt;/tafsir_chunk&gt;
  &lt;/tafsir_section_block&gt;
  &lt;tafsir_section_block&gt;
    &lt;tafsir_chunk&gt;
      &lt;historical_context&gt;ويقال : إن موسى ،</span></div></div><div class="l" title="```xml
&lt;tafsir_section&gt;
  &lt;tafsir_section_block&gt;
    &lt;tafsir_chunk&gt;يذكر تعالى أنه فرقهم في الأرض أمما ، &lt;linguistic_analysis&gt;أي : طوائف وفرقا&lt;/linguistic_analysis&gt; ،&lt;/tafsir_chunk&gt;
    &lt;tafsir_chunk&gt;&lt;cross_references&gt;كما قال [ تعالى ] &lt;quran_verse&gt;( وقلنا من بعده لبني إسرائيل اسكنوا الأرض فإذا جاء وعد الآخرة جئنا بكم لفيفا )&lt;/quran_verse&gt; &lt;source&gt;[ الإسراء : 104 ]&lt;/source&gt;&lt;/cross_references&gt;&lt;/tafsir_chunk&gt;
  &lt;/tafsir_section_block&gt;
  &lt;tafsir_section_block&gt;
    &lt;tafsir_chunk&gt; &lt;quran_verse&gt;( منهم الصالحون ومنهم دون ذلك )&lt;/quran_verse&gt; &lt;linguistic_analysis&gt;أي : فيهم الصالح وغير ذلك&lt;/linguistic_analysis&gt; ،&lt;/tafsir_chunk&gt;
    &lt;tafsir_chunk&gt; &lt;cross_references&gt;كما قالت الجن : &lt;quran_verse&gt;( وأنا منا الصالحون ومنا دون ذلك كنا طرائق قددا )&lt;/quran_verse&gt; &lt;source&gt;[ الجن : 11 ]&lt;/source&gt;&lt;/cross_references&gt; ،&lt;/tafsir_chunk&gt;
  &lt;/tafsir_section_block&gt;
  &lt;tafsir_section_block&gt;
    &lt;tafsir_chunk&gt; &lt;quran_verse&gt;( وبلوناهم )&lt;/quran_verse&gt; &lt;linguistic_analysis&gt;أي : اختبرناهم&lt;/linguistic_analysis&gt;&lt;/tafsir_chunk&gt;
    &lt;tafsir_chunk&gt; " tabindex="0" style="content-visibility: visible; transform: translate(0px, 2808px); height: 26px;"><div class="Bl"><span>```xml
&lt;tafsir_section&gt;
  &lt;tafsir_section_block&gt;
    &lt;tafsir_chunk&gt;يذكر تعالى أنه فرقهم في الأرض أمما ، &lt;linguistic_analysis&gt;أي : طوائف وفرقا&lt;/linguistic_analysis&gt; ،&lt;/tafsir_chunk&gt;
    &lt;tafsir_chunk&gt;&lt;cross_references&gt;كما قال [ تعالى ] &lt;quran_verse&gt;( وقلنا من بعده لبني إسرائيل اسكنوا الأرض فإذا جاء وعد الآخرة جئنا بكم لفيفا )&lt;/quran_verse&gt; &lt;source&gt;[ الإسراء : 104 ]&lt;/source&gt;&lt;/cross_references&gt;&lt;/tafsir_chunk&gt;
  &lt;/tafsir_section_block&gt;
  &lt;tafsir_section_block&gt;
    &lt;tafsir_chunk&gt; &lt;quran_verse&gt;( منهم الصالحون ومنهم دون ذلك )&lt;/quran_verse&gt; &lt;linguistic_analysis&gt;أي : فيهم الصالح وغير ذلك&lt;/linguistic_analysis&gt; ،&lt;/tafsir_chunk&gt;
    &lt;tafsir_chunk&gt; &lt;cross_references&gt;كما قالت الجن : &lt;quran_verse&gt;( وأنا منا الصالحون ومنا دون ذلك كنا طرائق قددا )&lt;/quran_verse&gt; &lt;source&gt;[ الجن : 11 ]&lt;/source&gt;&lt;/cross_references&gt; ،&lt;/tafsir_chunk&gt;
  &lt;/tafsir_section_block&gt;
  &lt;tafsir_section_block&gt;
    &lt;tafsir_chunk&gt; &lt;quran_verse&gt;( وبلوناهم )&lt;/quran_verse&gt; &lt;linguistic_analysis&gt;أي : اختبرناهم&lt;/linguistic_analysis&gt;&lt;/tafsir_chunk&gt;
    &lt;tafsir_chunk&gt; </span></div></div><div class="l Zo" title="```xml
&lt;tafsir_section&gt;
  &lt;tafsir_section_block&gt;
    &lt;tafsir_chunk&gt;ثم قال تعالى : &lt;quran_verse&gt;( فخلف من بعدهم خلف ورثوا الكتاب يأخذون عرض هذا الأدنى ويقولون سيغفر لنا وإن يأتهم عرض مثله يأخذوه )&lt;/quran_verse&gt;&lt;/tafsir_chunk&gt;
    &lt;tafsir_chunk&gt;يقول تعالى : فخلف من بعد ذلك الجيل الذين فيهم الصالح والطالح ، خلف آخر لا خير فيهم ، وقد ورثوا دراسة [ هذا ] الكتاب وهو التوراة&lt;/tafsir_chunk&gt;
    &lt;tafsir_chunk&gt;- &lt;source&gt;وقال مجاهد&lt;/source&gt; : &lt;opinions_of_scholars&gt;هم النصارى - وقد يكون أعم من ذلك&lt;/opinions_of_scholars&gt; ،&lt;/tafsir_chunk&gt;
    &lt;tafsir_chunk&gt;&lt;quran_verse&gt;( يأخذون عرض هذا الأدنى )&lt;/quran_verse&gt; &lt;linguistic_analysis&gt;أي : يعتاضون عن بذل الحق ونشره بعرض الحياة الدنيا&lt;/linguistic_analysis&gt; ، ويسوفون أنفسهم ويعدونها بالتوبة ، وكلما لاح لهم مثل الأول وقعوا فيه ; ولهذا قال : &lt;quran_verse&gt;( وإن يأتهم عرض مثله يأخذوه )&lt;/quran_verse&gt;&lt;/tafsir_chunk&gt;
  &lt;/tafsir_section_block&gt;
  &lt;tafsir_section_block&gt;
    &lt;tafsir_chunk&gt;كما &lt;source&gt;قال سعيد بن جبير&lt;/source&gt; : &lt;opinions_of_scholars&gt;يعملون الذنب ، ثم يستغفرون الله منه ، فإن " tabindex="0" style="content-visibility: visible; transform: translate(0px, 2834px); height: 26px;"><div class="Bl"><span>```xml
&lt;tafsir_section&gt;
  &lt;tafsir_section_block&gt;
    &lt;tafsir_chunk&gt;ثم قال تعالى : &lt;quran_verse&gt;( فخلف من بعدهم خلف ورثوا الكتاب يأخذون عرض هذا الأدنى ويقولون سيغفر لنا وإن يأتهم عرض مثله يأخذوه )&lt;/quran_verse&gt;&lt;/tafsir_chunk&gt;
    &lt;tafsir_chunk&gt;يقول تعالى : فخلف من بعد ذلك الجيل الذين فيهم الصالح والطالح ، خلف آخر لا خير فيهم ، وقد ورثوا دراسة [ هذا ] الكتاب وهو التوراة&lt;/tafsir_chunk&gt;
    &lt;tafsir_chunk&gt;- &lt;source&gt;وقال مجاهد&lt;/source&gt; : &lt;opinions_of_scholars&gt;هم النصارى - وقد يكون أعم من ذلك&lt;/opinions_of_scholars&gt; ،&lt;/tafsir_chunk&gt;
    &lt;tafsir_chunk&gt;&lt;quran_verse&gt;( يأخذون عرض هذا الأدنى )&lt;/quran_verse&gt; &lt;linguistic_analysis&gt;أي : يعتاضون عن بذل الحق ونشره بعرض الحياة الدنيا&lt;/linguistic_analysis&gt; ، ويسوفون أنفسهم ويعدونها بالتوبة ، وكلما لاح لهم مثل الأول وقعوا فيه ; ولهذا قال : &lt;quran_verse&gt;( وإن يأتهم عرض مثله يأخذوه )&lt;/quran_verse&gt;&lt;/tafsir_chunk&gt;
  &lt;/tafsir_section_block&gt;
  &lt;tafsir_section_block&gt;
    &lt;tafsir_chunk&gt;كما &lt;source&gt;قال سعيد بن جبير&lt;/source&gt; : &lt;opinions_of_scholars&gt;يعملون الذنب ، ثم يستغفرون الله منه ، فإن </span></div></div><div class="l" title="```xml
&lt;tafsir_section&gt;
  &lt;tafsir_section_block&gt;
    &lt;tafsir_chunk&gt;
      فقال تعالى &lt;quran_verse&gt;( والذين يمسكون بالكتاب )&lt;/quran_verse&gt;
    &lt;/tafsir_chunk&gt;
    &lt;tafsir_chunk&gt;
      &lt;opinions_of_scholars&gt;أي : &lt;command_and_prohibition&gt;اعتصموا به واقتدوا بأوامره ، وتركوا زواجره&lt;/command_and_prohibition&gt;&lt;/opinions_of_scholars&gt;
    &lt;/tafsir_chunk&gt;
    &lt;tafsir_chunk&gt;
      &lt;quran_verse&gt;( وأقاموا الصلاة إنا لا نضيع أجر المصلحين )&lt;/quran_verse&gt;
    &lt;/tafsir_chunk&gt;
  &lt;/tafsir_section_block&gt;
&lt;/tafsir_section&gt;
```" tabindex="0" style="content-visibility: visible; transform: translate(0px, 2860px); height: 26px;"><div class="Bl"><span>```xml
&lt;tafsir_section&gt;
  &lt;tafsir_section_block&gt;
    &lt;tafsir_chunk&gt;
      فقال تعالى &lt;quran_verse&gt;( والذين يمسكون بالكتاب )&lt;/quran_verse&gt;
    &lt;/tafsir_chunk&gt;
    &lt;tafsir_chunk&gt;
      &lt;opinions_of_scholars&gt;أي : &lt;command_and_prohibition&gt;اعتصموا به واقتدوا بأوامره ، وتركوا زواجره&lt;/command_and_prohibition&gt;&lt;/opinions_of_scholars&gt;
    &lt;/tafsir_chunk&gt;
    &lt;tafsir_chunk&gt;
      &lt;quran_verse&gt;( وأقاموا الصلاة إنا لا نضيع أجر المصلحين )&lt;/quran_verse&gt;
    &lt;/tafsir_chunk&gt;
  &lt;/tafsir_section_block&gt;
&lt;/tafsir_section&gt;
```</span></div></div><div class="l Zo" title="```xml
&lt;tafsir_section&gt;
  &lt;tafsir_section_block&gt;
    &lt;tafsir_chunk&gt;
      &lt;opinions_of_scholars&gt;
        &lt;isnad&gt;قال علي بن أبي طلحة ، عن ابن عباس قوله :&lt;/isnad&gt;
        &lt;quran_verse&gt;( وإذ نتقنا الجبل فوقهم )&lt;/quran_verse&gt;
        &lt;linguistic_analysis&gt;يقول : رفعناه ،&lt;/linguistic_analysis&gt;
        &lt;cross_references&gt;وهو قوله : &lt;quran_verse&gt;( ورفعنا فوقهم الطور بميثاقهم )&lt;/quran_verse&gt; [ النساء : 154 ]&lt;/cross_references&gt;
      &lt;/opinions_of_scholars&gt;
    &lt;/tafsir_chunk&gt;
  &lt;/tafsir_section_block&gt;
  &lt;tafsir_section_block&gt;
    &lt;tafsir_chunk&gt;
      &lt;opinions_of_scholars&gt;
        &lt;isnad&gt;وقال سفيان الثوري ، عن الأعمش ، عن سعيد بن جبير ، عن ابن عباس ،&lt;/isnad&gt;
        &lt;hadith&gt;رفعته الملائكة فوق رءوسهم .&lt;/hadith&gt;
      &lt;/opinions_of_scholars&gt;
    &lt;/tafsir_chunk&gt;
  &lt;/tafsir_section_block&gt;
  &lt;tafsir_section_block&gt;
    &lt;tafsir_chunk&gt;
      &lt;opinions_of_scholars&gt;
        &lt;isnad&gt;وقال القاسم بن أبي أيوب ، عن سعيد بن جبير ، عن ابن عباس قال :&lt;/isnad&gt;
        &lt;historical_context&gt;ثم سار بهم موسى ، عليه السلام ، متوجها نحو الأرض الم" tabindex="0" style="content-visibility: visible; transform: translate(0px, 2886px); height: 26px;"><div class="Bl"><span>```xml
&lt;tafsir_section&gt;
  &lt;tafsir_section_block&gt;
    &lt;tafsir_chunk&gt;
      &lt;opinions_of_scholars&gt;
        &lt;isnad&gt;قال علي بن أبي طلحة ، عن ابن عباس قوله :&lt;/isnad&gt;
        &lt;quran_verse&gt;( وإذ نتقنا الجبل فوقهم )&lt;/quran_verse&gt;
        &lt;linguistic_analysis&gt;يقول : رفعناه ،&lt;/linguistic_analysis&gt;
        &lt;cross_references&gt;وهو قوله : &lt;quran_verse&gt;( ورفعنا فوقهم الطور بميثاقهم )&lt;/quran_verse&gt; [ النساء : 154 ]&lt;/cross_references&gt;
      &lt;/opinions_of_scholars&gt;
    &lt;/tafsir_chunk&gt;
  &lt;/tafsir_section_block&gt;
  &lt;tafsir_section_block&gt;
    &lt;tafsir_chunk&gt;
      &lt;opinions_of_scholars&gt;
        &lt;isnad&gt;وقال سفيان الثوري ، عن الأعمش ، عن سعيد بن جبير ، عن ابن عباس ،&lt;/isnad&gt;
        &lt;hadith&gt;رفعته الملائكة فوق رءوسهم .&lt;/hadith&gt;
      &lt;/opinions_of_scholars&gt;
    &lt;/tafsir_chunk&gt;
  &lt;/tafsir_section_block&gt;
  &lt;tafsir_section_block&gt;
    &lt;tafsir_chunk&gt;
      &lt;opinions_of_scholars&gt;
        &lt;isnad&gt;وقال القاسم بن أبي أيوب ، عن سعيد بن جبير ، عن ابن عباس قال :&lt;/isnad&gt;
        &lt;historical_context&gt;ثم سار بهم موسى ، عليه السلام ، متوجها نحو الأرض الم</span></div></div><div class="l" title="```xml
&lt;tafsir_section&gt;
  &lt;tafsir_section_block&gt;
    &lt;tafsir_chunk&gt;
      &lt;opinions_of_scholars&gt;يخبر تعالى أنه استخرج ذرية بني آدم من أصلابهم ، شاهدين على أنفسهم أن الله ربهم ومليكهم ، وأنه لا إله إلا هو . كما أنه تعالى فطرهم على ذلك وجبلهم عليه ، قال تعالى : &lt;quran_verse&gt;( فأقم وجهك للدين حنيفا فطرة الله التي فطر الناس عليها لا تبديل لخلق الله )&lt;/quran_verse&gt; [ الروم : 30 ]&lt;/opinions_of_scholars&gt;
    &lt;/tafsir_chunk&gt;
    &lt;tafsir_chunk&gt;
      وفي &lt;source&gt;الصحيحين&lt;/source&gt; &lt;isnad&gt;عن أبي هريرة ، رضي الله عنه ، قال : قال رسول الله صلى الله عليه وسلم :&lt;/isnad&gt; &lt;hadith&gt;&quot; كل مولود يولد على الفطرة - وفي رواية : على هذه الملة - فأبواه يهودانه ، وينصرانه ، ويمجسانه ، كما تولد البهيمة بهيمة جمعاء ، هل تحسون فيها من جدعاء &quot;&lt;/hadith&gt;
    &lt;/tafsir_chunk&gt;
    &lt;tafsir_chunk&gt;
      وفي &lt;source&gt;صحيح مسلم&lt;/source&gt; ، &lt;isnad&gt;عن عياض بن حمار قال : قال رسول الله صلى الله عليه وسلم :&lt;/isnad&gt; &lt;hadith&gt;&quot; يقول الله [ تعالى ] إني خلقت عبادي حنفاء فجاءتهم الشياطين فاجتالتهم ، عن دينهم وحرمت عليهم ما أحللت لهم &quot;&lt;/hadith&gt;
    &lt;/tafsir_chunk" tabindex="0" style="content-visibility: visible; transform: translate(0px, 2912px); height: 26px;"><div class="Bl"><span>```xml
&lt;tafsir_section&gt;
  &lt;tafsir_section_block&gt;
    &lt;tafsir_chunk&gt;
      &lt;opinions_of_scholars&gt;يخبر تعالى أنه استخرج ذرية بني آدم من أصلابهم ، شاهدين على أنفسهم أن الله ربهم ومليكهم ، وأنه لا إله إلا هو . كما أنه تعالى فطرهم على ذلك وجبلهم عليه ، قال تعالى : &lt;quran_verse&gt;( فأقم وجهك للدين حنيفا فطرة الله التي فطر الناس عليها لا تبديل لخلق الله )&lt;/quran_verse&gt; [ الروم : 30 ]&lt;/opinions_of_scholars&gt;
    &lt;/tafsir_chunk&gt;
    &lt;tafsir_chunk&gt;
      وفي &lt;source&gt;الصحيحين&lt;/source&gt; &lt;isnad&gt;عن أبي هريرة ، رضي الله عنه ، قال : قال رسول الله صلى الله عليه وسلم :&lt;/isnad&gt; &lt;hadith&gt;" كل مولود يولد على الفطرة - وفي رواية : على هذه الملة - فأبواه يهودانه ، وينصرانه ، ويمجسانه ، كما تولد البهيمة بهيمة جمعاء ، هل تحسون فيها من جدعاء "&lt;/hadith&gt;
    &lt;/tafsir_chunk&gt;
    &lt;tafsir_chunk&gt;
      وفي &lt;source&gt;صحيح مسلم&lt;/source&gt; ، &lt;isnad&gt;عن عياض بن حمار قال : قال رسول الله صلى الله عليه وسلم :&lt;/isnad&gt; &lt;hadith&gt;" يقول الله [ تعالى ] إني خلقت عبادي حنفاء فجاءتهم الشياطين فاجتالتهم ، عن دينهم وحرمت عليهم ما أحللت لهم "&lt;/hadith&gt;
    &lt;/tafsir_chunk</span></div></div><div class="l Zo" title="```xml
&lt;tafsir_section&gt;
  &lt;tafsir_section_block&gt;
    &lt;tafsir_chunk&gt;
      &lt;opinions_of_scholars&gt;يخبر تعالى أنه استخرج ذرية بني آدم من أصلابهم ، شاهدين على أنفسهم أن الله ربهم ومليكهم ، وأنه لا إله إلا هو . كما أنه تعالى فطرهم على ذلك وجبلهم عليه ، قال تعالى :&lt;/opinions_of_scholars&gt;
      &lt;quran_verse&gt;( فأقم وجهك للدين حنيفا فطرة الله التي فطر الناس عليها لا تبديل لخلق الله )&lt;/quran_verse&gt;
      &lt;source&gt;[ الروم : 30 ]&lt;/source&gt;
    &lt;/tafsir_chunk&gt;
    &lt;tafsir_chunk&gt;
      &lt;source&gt;وفي الصحيحين&lt;/source&gt;
      &lt;isnad&gt;عن أبي هريرة ، رضي الله عنه ، قال : قال رسول الله صلى الله عليه وسلم :&lt;/isnad&gt;
      &lt;hadith&gt;&quot; كل مولود يولد على الفطرة - وفي رواية : على هذه الملة - فأبواه يهودانه ، وينصرانه ، ويمجسانه ، كما تولد البهيمة بهيمة جمعاء ، هل تحسون فيها من جدعاء &quot;&lt;/hadith&gt;
    &lt;/tafsir_chunk&gt;
    &lt;tafsir_chunk&gt;
      &lt;source&gt;وفي صحيح مسلم ،&lt;/source&gt;
      &lt;isnad&gt;عن عياض بن حمار قال : قال رسول الله صلى الله عليه وسلم :&lt;/isnad&gt;
      &lt;hadith&gt;&quot; يقول الله [ تعالى ] إني خلقت عبادي حنفاء فجاءتهم الشياطين فاجتالتهم ، عن دينهم و" tabindex="0" style="content-visibility: visible; transform: translate(0px, 2938px); height: 26px;"><div class="Bl"><span>```xml
&lt;tafsir_section&gt;
  &lt;tafsir_section_block&gt;
    &lt;tafsir_chunk&gt;
      &lt;opinions_of_scholars&gt;يخبر تعالى أنه استخرج ذرية بني آدم من أصلابهم ، شاهدين على أنفسهم أن الله ربهم ومليكهم ، وأنه لا إله إلا هو . كما أنه تعالى فطرهم على ذلك وجبلهم عليه ، قال تعالى :&lt;/opinions_of_scholars&gt;
      &lt;quran_verse&gt;( فأقم وجهك للدين حنيفا فطرة الله التي فطر الناس عليها لا تبديل لخلق الله )&lt;/quran_verse&gt;
      &lt;source&gt;[ الروم : 30 ]&lt;/source&gt;
    &lt;/tafsir_chunk&gt;
    &lt;tafsir_chunk&gt;
      &lt;source&gt;وفي الصحيحين&lt;/source&gt;
      &lt;isnad&gt;عن أبي هريرة ، رضي الله عنه ، قال : قال رسول الله صلى الله عليه وسلم :&lt;/isnad&gt;
      &lt;hadith&gt;" كل مولود يولد على الفطرة - وفي رواية : على هذه الملة - فأبواه يهودانه ، وينصرانه ، ويمجسانه ، كما تولد البهيمة بهيمة جمعاء ، هل تحسون فيها من جدعاء "&lt;/hadith&gt;
    &lt;/tafsir_chunk&gt;
    &lt;tafsir_chunk&gt;
      &lt;source&gt;وفي صحيح مسلم ،&lt;/source&gt;
      &lt;isnad&gt;عن عياض بن حمار قال : قال رسول الله صلى الله عليه وسلم :&lt;/isnad&gt;
      &lt;hadith&gt;" يقول الله [ تعالى ] إني خلقت عبادي حنفاء فجاءتهم الشياطين فاجتالتهم ، عن دينهم و</span></div></div><div class="l" title="```xml
&lt;tafsir_section&gt;
  &lt;tafsir_section_block&gt;
    &lt;tafsir_chunk&gt;
      &lt;opinions_of_scholars&gt;
        &lt;theological_points&gt;يخبر تعالى أنه استخرج ذرية بني آدم من أصلابهم ، شاهدين على أنفسهم أن الله ربهم ومليكهم ، وأنه لا إله إلا هو . كما أنه تعالى فطرهم على ذلك وجبلهم عليه&lt;/theological_points&gt;
      &lt;/opinions_of_scholars&gt;
      ، قال تعالى : &lt;quran_verse&gt;( فأقم وجهك للدين حنيفا فطرة الله التي فطر الناس عليها لا تبديل لخلق الله ) [ الروم : 30 ]&lt;/quran_verse&gt;
    &lt;/tafsir_chunk&gt;
    &lt;tafsir_chunk&gt;
      &lt;source&gt;وفي الصحيحين&lt;/source&gt;
      &lt;isnad&gt;عن أبي هريرة ، رضي الله عنه ، قال : قال رسول الله صلى الله عليه وسلم :&lt;/isnad&gt;
      &lt;hadith&gt;&quot; كل مولود يولد على الفطرة - وفي رواية : على هذه الملة - فأبواه يهودانه ، وينصرانه ، ويمجسانه ، كما تولد البهيمة بهيمة جمعاء ، هل تحسون فيها من جدعاء &quot;&lt;/hadith&gt;
    &lt;/tafsir_chunk&gt;
  &lt;/tafsir_section_block&gt;

  &lt;tafsir_section_block&gt;
    &lt;tafsir_chunk&gt;
      &lt;source&gt;وفي صحيح مسلم&lt;/source&gt;
      &lt;isnad&gt;، عن عياض بن حمار قال : قال رسول الله صلى الله عليه وسلم :&lt;/isnad&gt;
      &lt;had" tabindex="0" style="content-visibility: visible; transform: translate(0px, 2964px); height: 26px;"><div class="Bl"><span>```xml
&lt;tafsir_section&gt;
  &lt;tafsir_section_block&gt;
    &lt;tafsir_chunk&gt;
      &lt;opinions_of_scholars&gt;
        &lt;theological_points&gt;يخبر تعالى أنه استخرج ذرية بني آدم من أصلابهم ، شاهدين على أنفسهم أن الله ربهم ومليكهم ، وأنه لا إله إلا هو . كما أنه تعالى فطرهم على ذلك وجبلهم عليه&lt;/theological_points&gt;
      &lt;/opinions_of_scholars&gt;
      ، قال تعالى : &lt;quran_verse&gt;( فأقم وجهك للدين حنيفا فطرة الله التي فطر الناس عليها لا تبديل لخلق الله ) [ الروم : 30 ]&lt;/quran_verse&gt;
    &lt;/tafsir_chunk&gt;
    &lt;tafsir_chunk&gt;
      &lt;source&gt;وفي الصحيحين&lt;/source&gt;
      &lt;isnad&gt;عن أبي هريرة ، رضي الله عنه ، قال : قال رسول الله صلى الله عليه وسلم :&lt;/isnad&gt;
      &lt;hadith&gt;" كل مولود يولد على الفطرة - وفي رواية : على هذه الملة - فأبواه يهودانه ، وينصرانه ، ويمجسانه ، كما تولد البهيمة بهيمة جمعاء ، هل تحسون فيها من جدعاء "&lt;/hadith&gt;
    &lt;/tafsir_chunk&gt;
  &lt;/tafsir_section_block&gt;

  &lt;tafsir_section_block&gt;
    &lt;tafsir_chunk&gt;
      &lt;source&gt;وفي صحيح مسلم&lt;/source&gt;
      &lt;isnad&gt;، عن عياض بن حمار قال : قال رسول الله صلى الله عليه وسلم :&lt;/isnad&gt;
      &lt;had</span></div></div><div class="l Zo" title="```xml
&lt;tafsir_section&gt;
  &lt;tafsir_section_block&gt;
    &lt;tafsir_chunk&gt;
      &lt;source&gt;قال عبد الرزاق&lt;/source&gt;
      ،
      &lt;isnad&gt;عن سفيان الثوري ، عن الأعمش ومنصور ، عن أبي الضحى ، عن مسروق ، عن عبد الله بن مسعود ، رضي الله عنه&lt;/isnad&gt;
      ، في قوله تعالى :
      &lt;quran_verse&gt;( واتل عليهم نبأ الذي آتيناه آياتنا فانسلخ منها [ فأتبعه ] )&lt;/quran_verse&gt;
      الآية ، قال :
    &lt;/tafsir_chunk&gt;
    &lt;tafsir_chunk&gt;
      &lt;opinions_of_scholars&gt;هو رجل من بني إسرائيل ، يقال له : بلعم بن أبر&lt;/opinions_of_scholars&gt;
      .
    &lt;/tafsir_chunk&gt;
    &lt;tafsir_chunk&gt;
      وكذا رواه
      &lt;source&gt;شعبة&lt;/source&gt;
      وغير واحد ،
      &lt;isnad&gt;عن منصور&lt;/isnad&gt;
      ، به .
    &lt;/tafsir_chunk&gt;
  &lt;/tafsir_section_block&gt;
  &lt;tafsir_section_block&gt;
    &lt;tafsir_chunk&gt;
      &lt;source&gt;وقال سعيد بن أبي عروبة&lt;/source&gt;
      ،
      &lt;isnad&gt;عن قتادة ، عن ابن عباس [ رضي الله عنهما ]&lt;/isnad&gt;
      &lt;opinions_of_scholars&gt;هو صيفي بن الراهب&lt;/opinions_of_scholars&gt;
      .
    &lt;/tafsir_chunk&gt;
    &lt;tafsir_chunk&gt;
      &lt;source&gt;قال قتادة : وقال كعب&lt;/sourc" tabindex="0" style="content-visibility: visible; transform: translate(0px, 2990px); height: 26px;"><div class="Bl"><span>```xml
&lt;tafsir_section&gt;
  &lt;tafsir_section_block&gt;
    &lt;tafsir_chunk&gt;
      &lt;source&gt;قال عبد الرزاق&lt;/source&gt;
      ،
      &lt;isnad&gt;عن سفيان الثوري ، عن الأعمش ومنصور ، عن أبي الضحى ، عن مسروق ، عن عبد الله بن مسعود ، رضي الله عنه&lt;/isnad&gt;
      ، في قوله تعالى :
      &lt;quran_verse&gt;( واتل عليهم نبأ الذي آتيناه آياتنا فانسلخ منها [ فأتبعه ] )&lt;/quran_verse&gt;
      الآية ، قال :
    &lt;/tafsir_chunk&gt;
    &lt;tafsir_chunk&gt;
      &lt;opinions_of_scholars&gt;هو رجل من بني إسرائيل ، يقال له : بلعم بن أبر&lt;/opinions_of_scholars&gt;
      .
    &lt;/tafsir_chunk&gt;
    &lt;tafsir_chunk&gt;
      وكذا رواه
      &lt;source&gt;شعبة&lt;/source&gt;
      وغير واحد ،
      &lt;isnad&gt;عن منصور&lt;/isnad&gt;
      ، به .
    &lt;/tafsir_chunk&gt;
  &lt;/tafsir_section_block&gt;
  &lt;tafsir_section_block&gt;
    &lt;tafsir_chunk&gt;
      &lt;source&gt;وقال سعيد بن أبي عروبة&lt;/source&gt;
      ،
      &lt;isnad&gt;عن قتادة ، عن ابن عباس [ رضي الله عنهما ]&lt;/isnad&gt;
      &lt;opinions_of_scholars&gt;هو صيفي بن الراهب&lt;/opinions_of_scholars&gt;
      .
    &lt;/tafsir_chunk&gt;
    &lt;tafsir_chunk&gt;
      &lt;source&gt;قال قتادة : وقال كعب&lt;/sourc</span></div></div><div class="l" title="```xml
&lt;tafsir_section&gt;
  &lt;tafsir_section_block&gt;
    &lt;tafsir_chunk&gt;
      &lt;quran_verse&gt;وقوله تعالى : ( ولو شئنا لرفعناه بها ولكنه أخلد إلى الأرض واتبع هواه )&lt;/quran_verse&gt;
      &lt;opinions_of_scholars&gt;
        يقول تعالى :
        &lt;quran_verse&gt;( ولو شئنا لرفعناه بها )&lt;/quran_verse&gt;
        أي :
        &lt;literal_interpretation&gt;لرفعناه من التدنس عن قاذورات الدنيا بالآيات التي آتيناه إياها ،&lt;/literal_interpretation&gt;
        &lt;quran_verse&gt;( ولكنه أخلد إلى الأرض )&lt;/quran_verse&gt;
        أي :
        &lt;literal_interpretation&gt;مال إلى زينة الدنيا وزهرتها ، وأقبل على لذاتها ونعيمها ، وغرته كما غرت غيره من غير أولي البصائر والنهى .&lt;/literal_interpretation&gt;
      &lt;/opinions_of_scholars&gt;
    &lt;/tafsir_chunk&gt;
  &lt;/tafsir_section_block&gt;

  &lt;tafsir_section_block&gt;
    &lt;tafsir_chunk&gt;
      &lt;source&gt;وقال أبو الزاهرية&lt;/source&gt;
      في قوله تعالى :
      &lt;quran_verse&gt;( ولكنه أخلد إلى الأرض )&lt;/quran_verse&gt;
      &lt;opinions_of_scholars&gt;
        قال : تراءى له الشيطان على غلوة من قنطرة بانياس ، فسجدت الحمارة لله ، وسجد بلعام للشيطان .
   " tabindex="0" style="content-visibility: hidden; transform: translate(0px, 3016px); height: 26px;"><div class="Bl"><span>```xml
&lt;tafsir_section&gt;
  &lt;tafsir_section_block&gt;
    &lt;tafsir_chunk&gt;
      &lt;quran_verse&gt;وقوله تعالى : ( ولو شئنا لرفعناه بها ولكنه أخلد إلى الأرض واتبع هواه )&lt;/quran_verse&gt;
      &lt;opinions_of_scholars&gt;
        يقول تعالى :
        &lt;quran_verse&gt;( ولو شئنا لرفعناه بها )&lt;/quran_verse&gt;
        أي :
        &lt;literal_interpretation&gt;لرفعناه من التدنس عن قاذورات الدنيا بالآيات التي آتيناه إياها ،&lt;/literal_interpretation&gt;
        &lt;quran_verse&gt;( ولكنه أخلد إلى الأرض )&lt;/quran_verse&gt;
        أي :
        &lt;literal_interpretation&gt;مال إلى زينة الدنيا وزهرتها ، وأقبل على لذاتها ونعيمها ، وغرته كما غرت غيره من غير أولي البصائر والنهى .&lt;/literal_interpretation&gt;
      &lt;/opinions_of_scholars&gt;
    &lt;/tafsir_chunk&gt;
  &lt;/tafsir_section_block&gt;

  &lt;tafsir_section_block&gt;
    &lt;tafsir_chunk&gt;
      &lt;source&gt;وقال أبو الزاهرية&lt;/source&gt;
      في قوله تعالى :
      &lt;quran_verse&gt;( ولكنه أخلد إلى الأرض )&lt;/quran_verse&gt;
      &lt;opinions_of_scholars&gt;
        قال : تراءى له الشيطان على غلوة من قنطرة بانياس ، فسجدت الحمارة لله ، وسجد بلعام للشيطان .
   </span></div></div><div class="l Zo" title="```xml
&lt;tafsir_section&gt;
  &lt;tafsir_section_block&gt;
    &lt;tafsir_chunk&gt;
      وقوله : &lt;quran_verse&gt;( ساء مثلا القوم الذين كذبوا بآياتنا وأنفسهم كانوا يظلمون )&lt;/quran_verse&gt;
    &lt;/tafsir_chunk&gt;
    &lt;tafsir_chunk&gt;
      &lt;opinions_of_scholars&gt;
        &lt;parabolic_meaning&gt;يقول تعالى ساء مثلا مثل القوم الذين كذبوا بآياتنا ، أي : ساء مثلهم أن شبهوا بالكلاب التي لا همة لها إلا في تحصيل أكلة أو شهوة ، فمن خرج عن حيز العلم والهدى وأقبل على شهوة نفسه ، واتبع هواه ، صار شبيها بالكلب ، وبئس المثل مثله ;&lt;/parabolic_meaning&gt;
      &lt;/opinions_of_scholars&gt;
    &lt;/tafsir_chunk&gt;
    &lt;tafsir_chunk&gt;
      &lt;hadith_support&gt;ولهذا ثبت &lt;source&gt;في الصحيح&lt;/source&gt; أن رسول الله صلى الله عليه وسلم قال : &lt;hadith&gt;&quot; ليس لنا مثل السوء ، العائد في هبته كالكلب يعود في قيئه &quot;&lt;/hadith&gt;&lt;/hadith_support&gt;
    &lt;/tafsir_chunk&gt;
  &lt;/tafsir_section_block&gt;
  &lt;tafsir_section_block&gt;
    &lt;tafsir_chunk&gt;
      وقوله : &lt;quran_verse&gt;( وأنفسهم كانوا يظلمون )&lt;/quran_verse&gt;
    &lt;/tafsir_chunk&gt;
    &lt;tafsir_chunk&gt;
      &lt;opinions_of_scholars&gt;
        &lt;theological_points&gt;أ" tabindex="0" style="content-visibility: hidden; transform: translate(0px, 3042px); height: 26px;"><div class="Bl"><span>```xml
&lt;tafsir_section&gt;
  &lt;tafsir_section_block&gt;
    &lt;tafsir_chunk&gt;
      وقوله : &lt;quran_verse&gt;( ساء مثلا القوم الذين كذبوا بآياتنا وأنفسهم كانوا يظلمون )&lt;/quran_verse&gt;
    &lt;/tafsir_chunk&gt;
    &lt;tafsir_chunk&gt;
      &lt;opinions_of_scholars&gt;
        &lt;parabolic_meaning&gt;يقول تعالى ساء مثلا مثل القوم الذين كذبوا بآياتنا ، أي : ساء مثلهم أن شبهوا بالكلاب التي لا همة لها إلا في تحصيل أكلة أو شهوة ، فمن خرج عن حيز العلم والهدى وأقبل على شهوة نفسه ، واتبع هواه ، صار شبيها بالكلب ، وبئس المثل مثله ;&lt;/parabolic_meaning&gt;
      &lt;/opinions_of_scholars&gt;
    &lt;/tafsir_chunk&gt;
    &lt;tafsir_chunk&gt;
      &lt;hadith_support&gt;ولهذا ثبت &lt;source&gt;في الصحيح&lt;/source&gt; أن رسول الله صلى الله عليه وسلم قال : &lt;hadith&gt;" ليس لنا مثل السوء ، العائد في هبته كالكلب يعود في قيئه "&lt;/hadith&gt;&lt;/hadith_support&gt;
    &lt;/tafsir_chunk&gt;
  &lt;/tafsir_section_block&gt;
  &lt;tafsir_section_block&gt;
    &lt;tafsir_chunk&gt;
      وقوله : &lt;quran_verse&gt;( وأنفسهم كانوا يظلمون )&lt;/quran_verse&gt;
    &lt;/tafsir_chunk&gt;
    &lt;tafsir_chunk&gt;
      &lt;opinions_of_scholars&gt;
        &lt;theological_points&gt;أ</span></div></div><div class="l" title="```xml
&lt;tafsir_section&gt;
  &lt;tafsir_section_block&gt;
    &lt;tafsir_chunk&gt;
      &lt;theological_points&gt;يقول تعالى : من هداه الله فإنه لا مضل له ، ومن أضله فقد خاب وخسر وضل لا محالة ، فإنه تعالى ما شاء كان ، وما لم يشأ لم يكن ;&lt;/theological_points&gt;
    &lt;/tafsir_chunk&gt;
  &lt;/tafsir_section_block&gt;
  &lt;tafsir_section_block&gt;
    &lt;tafsir_chunk&gt;
      &lt;hadith_support&gt;
        &lt;isnad&gt;ولهذا جاء في حديث ابن مسعود :&lt;/isnad&gt;
      &lt;/hadith_support&gt;
    &lt;/tafsir_chunk&gt;
    &lt;tafsir_chunk&gt;
      &lt;hadith_support&gt;
        &lt;hadith&gt;&quot; إن الحمد لله ، نحمده ونستعينه ونستهديه ونستغفره ، ونعوذ بالله من شرور أنفسنا ومن سيئات أعمالنا ، من يهده الله فلا مضل له ، ومن يضلل الله فلا هادي له ، وأشهد أن لا إله إلا الله وحده لا شريك له ، وأشهد أن محمدا عبده ورسوله &quot; .&lt;/hadith&gt;
      &lt;/hadith_support&gt;
    &lt;/tafsir_chunk&gt;
    &lt;tafsir_chunk&gt;
      &lt;source&gt;الحديث بتمامه رواه الإمام أحمد ، وأهل السنن ، وغيرهم&lt;/source&gt;
    &lt;/tafsir_chunk&gt;
  &lt;/tafsir_section_block&gt;
&lt;/tafsir_section&gt;
```" tabindex="0" style="content-visibility: hidden; transform: translate(0px, 3068px); height: 26px;"><div class="Bl"><span>```xml
&lt;tafsir_section&gt;
  &lt;tafsir_section_block&gt;
    &lt;tafsir_chunk&gt;
      &lt;theological_points&gt;يقول تعالى : من هداه الله فإنه لا مضل له ، ومن أضله فقد خاب وخسر وضل لا محالة ، فإنه تعالى ما شاء كان ، وما لم يشأ لم يكن ;&lt;/theological_points&gt;
    &lt;/tafsir_chunk&gt;
  &lt;/tafsir_section_block&gt;
  &lt;tafsir_section_block&gt;
    &lt;tafsir_chunk&gt;
      &lt;hadith_support&gt;
        &lt;isnad&gt;ولهذا جاء في حديث ابن مسعود :&lt;/isnad&gt;
      &lt;/hadith_support&gt;
    &lt;/tafsir_chunk&gt;
    &lt;tafsir_chunk&gt;
      &lt;hadith_support&gt;
        &lt;hadith&gt;" إن الحمد لله ، نحمده ونستعينه ونستهديه ونستغفره ، ونعوذ بالله من شرور أنفسنا ومن سيئات أعمالنا ، من يهده الله فلا مضل له ، ومن يضلل الله فلا هادي له ، وأشهد أن لا إله إلا الله وحده لا شريك له ، وأشهد أن محمدا عبده ورسوله " .&lt;/hadith&gt;
      &lt;/hadith_support&gt;
    &lt;/tafsir_chunk&gt;
    &lt;tafsir_chunk&gt;
      &lt;source&gt;الحديث بتمامه رواه الإمام أحمد ، وأهل السنن ، وغيرهم&lt;/source&gt;
    &lt;/tafsir_chunk&gt;
  &lt;/tafsir_section_block&gt;
&lt;/tafsir_section&gt;
```</span></div></div><div class="l Zo" title="```xml
&lt;tafsir_section&gt;
  &lt;tafsir_section_block&gt;
    &lt;tafsir_chunk&gt;
      يقول تعالى : ( &lt;quran_verse&gt;ولقد ذرأنا&lt;/quran_verse&gt; ) &lt;opinions_of_scholars&gt;أي : &lt;linguistic_analysis&gt;خلقنا وجعلنا&lt;/linguistic_analysis&gt;&lt;/opinions_of_scholars&gt; ( &lt;quran_verse&gt;لجهنم كثيرا من الجن والإنس&lt;/quran_verse&gt; ) &lt;opinions_of_scholars&gt;أي : هيأناهم لها ، وبعمل أهلها يعملون&lt;/opinions_of_scholars&gt; ،
    &lt;/tafsir_chunk&gt;
    &lt;tafsir_chunk&gt;
      &lt;theological_points&gt;فإنه تعالى لما أراد أن يخلق الخلائق ، علم ما هم عاملون قبل كونهم ، فكتب ذلك عنده في كتاب قبل أن يخلق السماوات والأرض بخمسين ألف سنة&lt;/theological_points&gt; ،
    &lt;/tafsir_chunk&gt;
  &lt;/tafsir_section_block&gt;
  &lt;tafsir_section_block&gt;
    &lt;tafsir_chunk&gt;
      &lt;hadith_support&gt;كما ورد في &lt;source&gt;صحيح مسلم&lt;/source&gt; ، عن &lt;isnad&gt;عبد الله بن عمرو أن رسول الله صلى الله عليه وسلم قال&lt;/isnad&gt; : &quot; &lt;hadith&gt;إن الله قدر مقادير الخلق قبل أن يخلق السماوات والأرض بخمسين ألف سنة ، وكان عرشه على الماء&lt;/hadith&gt; &quot;&lt;/hadith_support&gt;
    &lt;/tafsir_chunk&gt;
  &lt;/tafsir_section_block&gt;
  &lt;tafsir_section_block&gt;
  " tabindex="0" style="content-visibility: hidden; transform: translate(0px, 3094px); height: 26px;"><div class="Bl"><span>```xml
&lt;tafsir_section&gt;
  &lt;tafsir_section_block&gt;
    &lt;tafsir_chunk&gt;
      يقول تعالى : ( &lt;quran_verse&gt;ولقد ذرأنا&lt;/quran_verse&gt; ) &lt;opinions_of_scholars&gt;أي : &lt;linguistic_analysis&gt;خلقنا وجعلنا&lt;/linguistic_analysis&gt;&lt;/opinions_of_scholars&gt; ( &lt;quran_verse&gt;لجهنم كثيرا من الجن والإنس&lt;/quran_verse&gt; ) &lt;opinions_of_scholars&gt;أي : هيأناهم لها ، وبعمل أهلها يعملون&lt;/opinions_of_scholars&gt; ،
    &lt;/tafsir_chunk&gt;
    &lt;tafsir_chunk&gt;
      &lt;theological_points&gt;فإنه تعالى لما أراد أن يخلق الخلائق ، علم ما هم عاملون قبل كونهم ، فكتب ذلك عنده في كتاب قبل أن يخلق السماوات والأرض بخمسين ألف سنة&lt;/theological_points&gt; ،
    &lt;/tafsir_chunk&gt;
  &lt;/tafsir_section_block&gt;
  &lt;tafsir_section_block&gt;
    &lt;tafsir_chunk&gt;
      &lt;hadith_support&gt;كما ورد في &lt;source&gt;صحيح مسلم&lt;/source&gt; ، عن &lt;isnad&gt;عبد الله بن عمرو أن رسول الله صلى الله عليه وسلم قال&lt;/isnad&gt; : " &lt;hadith&gt;إن الله قدر مقادير الخلق قبل أن يخلق السماوات والأرض بخمسين ألف سنة ، وكان عرشه على الماء&lt;/hadith&gt; "&lt;/hadith_support&gt;
    &lt;/tafsir_chunk&gt;
  &lt;/tafsir_section_block&gt;
  &lt;tafsir_section_block&gt;
  </span></div></div><div class="l" title="```xml
&lt;tafsir_section&gt;
  &lt;tafsir_section_block&gt;
    &lt;tafsir_chunk&gt;
      &lt;isnad&gt;عن أبي هريرة ، رضي الله عنه ،&lt;/isnad&gt; قال : &lt;hadith&gt;قال رسول الله صلى الله عليه وسلم : &quot; إن لله تسعا وتسعين اسما مائة إلا واحدا ، من أحصاها دخل الجنة ، وهو وتر يحب الوتر &quot; .&lt;/hadith&gt;
    &lt;/tafsir_chunk&gt;
    &lt;tafsir_chunk&gt;
      &lt;source&gt;أخرجاه في الصحيحين&lt;/source&gt; &lt;isnad&gt;من حديث سفيان بن عيينة ، عن أبي الزناد ، عن الأعرج ، عنه&lt;/isnad&gt; &lt;source&gt;رواه البخاري&lt;/source&gt; ، &lt;isnad&gt;عن أبي اليمان ، عن شعيب بن أبي حمزة ، عن أبي الزناد به&lt;/isnad&gt; &lt;source&gt;وأخرجه الترمذي&lt;/source&gt; ، &lt;isnad&gt;عن الجوزجاني ، عن صفوان بن صالح ، عن الوليد بن مسلم ، عن شعيب&lt;/isnad&gt; فذكر بسنده مثله ، وزاد بعد قوله : &quot; يحب الوتر &quot; : &lt;hadith&gt;هو الله الذي لا إله إلا هو الرحمن الرحيم ، الملك ، القدوس ، السلام ، المؤمن ، المهيمن ، العزيز ، الجبار ، المتكبر ، الخالق ، البارئ ، المصور ، الغفار ، القهار ، الوهاب ، الرزاق ، الفتاح ، العليم ، القابض ، الباسط ، الخافض ، الرافع ، المعز ، المذل ، السميع ، البصير ، الحكم ، العدل ، اللطيف ، الخبير ، الحليم ، العظيم ، الغفور ، الشكور ،" tabindex="0" style="content-visibility: hidden; transform: translate(0px, 3120px); height: 26px;"><div class="Bl"><span>```xml
&lt;tafsir_section&gt;
  &lt;tafsir_section_block&gt;
    &lt;tafsir_chunk&gt;
      &lt;isnad&gt;عن أبي هريرة ، رضي الله عنه ،&lt;/isnad&gt; قال : &lt;hadith&gt;قال رسول الله صلى الله عليه وسلم : " إن لله تسعا وتسعين اسما مائة إلا واحدا ، من أحصاها دخل الجنة ، وهو وتر يحب الوتر " .&lt;/hadith&gt;
    &lt;/tafsir_chunk&gt;
    &lt;tafsir_chunk&gt;
      &lt;source&gt;أخرجاه في الصحيحين&lt;/source&gt; &lt;isnad&gt;من حديث سفيان بن عيينة ، عن أبي الزناد ، عن الأعرج ، عنه&lt;/isnad&gt; &lt;source&gt;رواه البخاري&lt;/source&gt; ، &lt;isnad&gt;عن أبي اليمان ، عن شعيب بن أبي حمزة ، عن أبي الزناد به&lt;/isnad&gt; &lt;source&gt;وأخرجه الترمذي&lt;/source&gt; ، &lt;isnad&gt;عن الجوزجاني ، عن صفوان بن صالح ، عن الوليد بن مسلم ، عن شعيب&lt;/isnad&gt; فذكر بسنده مثله ، وزاد بعد قوله : " يحب الوتر " : &lt;hadith&gt;هو الله الذي لا إله إلا هو الرحمن الرحيم ، الملك ، القدوس ، السلام ، المؤمن ، المهيمن ، العزيز ، الجبار ، المتكبر ، الخالق ، البارئ ، المصور ، الغفار ، القهار ، الوهاب ، الرزاق ، الفتاح ، العليم ، القابض ، الباسط ، الخافض ، الرافع ، المعز ، المذل ، السميع ، البصير ، الحكم ، العدل ، اللطيف ، الخبير ، الحليم ، العظيم ، الغفور ، الشكور ،</span></div></div><div class="l Zo" title="```xml
&lt;tafsir_section&gt;
  &lt;tafsir_section_block&gt;
    &lt;tafsir_chunk&gt;
      يقول تعالى : &lt;quran_verse&gt;( وممن خلقنا )&lt;/quran_verse&gt; &lt;linguistic_analysis&gt;أي : ومن الأمم ) أمة ) قائمة بالحق ، قولا وعملا&lt;/linguistic_analysis&gt;
    &lt;/tafsir_chunk&gt;
    &lt;tafsir_chunk&gt;
      &lt;quran_verse&gt;( يهدون بالحق )&lt;/quran_verse&gt; &lt;linguistic_analysis&gt;يقولونه ويدعون إليه ،&lt;/linguistic_analysis&gt;
    &lt;/tafsir_chunk&gt;
    &lt;tafsir_chunk&gt;
      &lt;quran_verse&gt;( وبه يعدلون )&lt;/quran_verse&gt; &lt;linguistic_analysis&gt;يعملون ويقضون .&lt;/linguistic_analysis&gt;
    &lt;/tafsir_chunk&gt;
  &lt;/tafsir_section_block&gt;
  &lt;tafsir_section_block&gt;
    &lt;tafsir_chunk&gt;
      &lt;opinions_of_scholars&gt;وقد جاء في الآثار : أن المراد بهذه الأمة المذكورة في الآية ، هي هذه الأمة المحمدية .&lt;/opinions_of_scholars&gt;
    &lt;/tafsir_chunk&gt;
  &lt;/tafsir_section_block&gt;
  &lt;tafsir_section_block&gt;
    &lt;tafsir_chunk&gt;
      &lt;hadith_support&gt;&lt;isnad&gt;قال سعيد ، عن قتادة&lt;/isnad&gt; في &lt;opinions_of_scholars&gt;تفسير هذه الآية : بلغنا أن نبي الله صلى الله عليه وسلم كان يقول إذا قرأ هذه الآية :&lt;/opinions_of_scholars&gt; " tabindex="0" style="content-visibility: hidden; transform: translate(0px, 3146px); height: 26px;"><div class="Bl"><span>```xml
&lt;tafsir_section&gt;
  &lt;tafsir_section_block&gt;
    &lt;tafsir_chunk&gt;
      يقول تعالى : &lt;quran_verse&gt;( وممن خلقنا )&lt;/quran_verse&gt; &lt;linguistic_analysis&gt;أي : ومن الأمم ) أمة ) قائمة بالحق ، قولا وعملا&lt;/linguistic_analysis&gt;
    &lt;/tafsir_chunk&gt;
    &lt;tafsir_chunk&gt;
      &lt;quran_verse&gt;( يهدون بالحق )&lt;/quran_verse&gt; &lt;linguistic_analysis&gt;يقولونه ويدعون إليه ،&lt;/linguistic_analysis&gt;
    &lt;/tafsir_chunk&gt;
    &lt;tafsir_chunk&gt;
      &lt;quran_verse&gt;( وبه يعدلون )&lt;/quran_verse&gt; &lt;linguistic_analysis&gt;يعملون ويقضون .&lt;/linguistic_analysis&gt;
    &lt;/tafsir_chunk&gt;
  &lt;/tafsir_section_block&gt;
  &lt;tafsir_section_block&gt;
    &lt;tafsir_chunk&gt;
      &lt;opinions_of_scholars&gt;وقد جاء في الآثار : أن المراد بهذه الأمة المذكورة في الآية ، هي هذه الأمة المحمدية .&lt;/opinions_of_scholars&gt;
    &lt;/tafsir_chunk&gt;
  &lt;/tafsir_section_block&gt;
  &lt;tafsir_section_block&gt;
    &lt;tafsir_chunk&gt;
      &lt;hadith_support&gt;&lt;isnad&gt;قال سعيد ، عن قتادة&lt;/isnad&gt; في &lt;opinions_of_scholars&gt;تفسير هذه الآية : بلغنا أن نبي الله صلى الله عليه وسلم كان يقول إذا قرأ هذه الآية :&lt;/opinions_of_scholars&gt; </span></div></div><div class="l" title="```xml
&lt;tafsir_section&gt;
  &lt;tafsir_section_block&gt;
    &lt;tafsir_chunk&gt;
      يقول تعالى : &lt;quran_verse&gt;( والذين كذبوا بآياتنا سنستدرجهم من حيث لا يعلمون )&lt;/quran_verse&gt;
    &lt;/tafsir_chunk&gt;
    &lt;tafsir_chunk&gt;
      &lt;opinions_of_scholars&gt;ومعناه : أنه يفتح لهم أبواب الرزق ووجوه المعاش في الدنيا ، حتى يغتروا بما هم فيه ويعتقدوا أنهم على شيء ،&lt;/opinions_of_scholars&gt;
    &lt;/tafsir_chunk&gt;
    &lt;tafsir_chunk&gt;
      &lt;cross_references&gt;كما قال تعالى : &lt;quran_verse&gt;( فلما نسوا ما ذكروا به فتحنا عليهم أبواب كل شيء حتى إذا فرحوا بما أوتوا أخذناهم بغتة فإذا هم مبلسون فقطع دابر القوم الذين ظلموا والحمد لله رب العالمين )&lt;/quran_verse&gt; &lt;source&gt;[ الأنعام : 44 ، 45 ]&lt;/source&gt;&lt;/cross_references&gt;
    &lt;/tafsir_chunk&gt;
  &lt;/tafsir_section_block&gt;
&lt;/tafsir_section&gt;
```" tabindex="0" style="content-visibility: hidden; transform: translate(0px, 3172px); height: 26px;"><div class="Bl"><span>```xml
&lt;tafsir_section&gt;
  &lt;tafsir_section_block&gt;
    &lt;tafsir_chunk&gt;
      يقول تعالى : &lt;quran_verse&gt;( والذين كذبوا بآياتنا سنستدرجهم من حيث لا يعلمون )&lt;/quran_verse&gt;
    &lt;/tafsir_chunk&gt;
    &lt;tafsir_chunk&gt;
      &lt;opinions_of_scholars&gt;ومعناه : أنه يفتح لهم أبواب الرزق ووجوه المعاش في الدنيا ، حتى يغتروا بما هم فيه ويعتقدوا أنهم على شيء ،&lt;/opinions_of_scholars&gt;
    &lt;/tafsir_chunk&gt;
    &lt;tafsir_chunk&gt;
      &lt;cross_references&gt;كما قال تعالى : &lt;quran_verse&gt;( فلما نسوا ما ذكروا به فتحنا عليهم أبواب كل شيء حتى إذا فرحوا بما أوتوا أخذناهم بغتة فإذا هم مبلسون فقطع دابر القوم الذين ظلموا والحمد لله رب العالمين )&lt;/quran_verse&gt; &lt;source&gt;[ الأنعام : 44 ، 45 ]&lt;/source&gt;&lt;/cross_references&gt;
    &lt;/tafsir_chunk&gt;
  &lt;/tafsir_section_block&gt;
&lt;/tafsir_section&gt;
```</span></div></div><div class="l Zo" title="```xml
&lt;tafsir_section&gt;
  &lt;tafsir_section_block&gt;
    &lt;tafsir_chunk&gt;ولهذا قال تعالى : &lt;quran_verse&gt;( وأملي لهم )&lt;/quran_verse&gt; أي : &lt;linguistic_analysis&gt;وسأملي لهم ، أطول لهم ما هم فيه&lt;/linguistic_analysis&gt;&lt;/tafsir_chunk&gt;
    &lt;tafsir_chunk&gt;&lt;quran_verse&gt;) إن كيدي متين )&lt;/quran_verse&gt; أي : &lt;linguistic_analysis&gt;قوي شديد .&lt;/linguistic_analysis&gt;&lt;/tafsir_chunk&gt;
  &lt;/tafsir_section_block&gt;
&lt;/tafsir_section&gt;
```" tabindex="0" style="content-visibility: hidden; transform: translate(0px, 3198px); height: 26px;"><div class="Bl"><span>```xml
&lt;tafsir_section&gt;
  &lt;tafsir_section_block&gt;
    &lt;tafsir_chunk&gt;ولهذا قال تعالى : &lt;quran_verse&gt;( وأملي لهم )&lt;/quran_verse&gt; أي : &lt;linguistic_analysis&gt;وسأملي لهم ، أطول لهم ما هم فيه&lt;/linguistic_analysis&gt;&lt;/tafsir_chunk&gt;
    &lt;tafsir_chunk&gt;&lt;quran_verse&gt;) إن كيدي متين )&lt;/quran_verse&gt; أي : &lt;linguistic_analysis&gt;قوي شديد .&lt;/linguistic_analysis&gt;&lt;/tafsir_chunk&gt;
  &lt;/tafsir_section_block&gt;
&lt;/tafsir_section&gt;
```</span></div></div><div class="l" title="```xml
&lt;tafsir_section&gt;
  &lt;tafsir_section_block&gt;
    &lt;tafsir_chunk&gt;
      &lt;opinions_of_scholars&gt;يقول تعالى : &lt;quran_verse&gt;( أولم يتفكروا )&lt;/quran_verse&gt; هؤلاء المكذبون بآياتنا &lt;quran_verse&gt;( ما بصاحبهم )&lt;/quran_verse&gt; يعني محمدا - صلوات الله وسلامه عليه &lt;quran_verse&gt;( من جنة )&lt;/quran_verse&gt; أي : ليس به جنون ، بل هو رسول الله حقا دعا إلى حق ، &lt;quran_verse&gt;( إن هو إلا نذير مبين )&lt;/quran_verse&gt; أي : ظاهر لمن كان له قلب ولب يعقل به ويعي به ،&lt;/opinions_of_scholars&gt;
    &lt;/tafsir_chunk&gt;
    &lt;tafsir_chunk&gt;
      كما قال تعالى : &lt;cross_references&gt;&lt;quran_verse&gt;( وما صاحبكم بمجنون )&lt;/quran_verse&gt;&lt;/cross_references&gt; &lt;source&gt;[ التكوير : 22 ]&lt;/source&gt; ،
    &lt;/tafsir_chunk&gt;
    &lt;tafsir_chunk&gt;
      وقال تعالى : &lt;cross_references&gt;&lt;quran_verse&gt;( قل إنما أعظكم بواحدة أن تقوموا لله مثنى وفرادى ثم تتفكروا ما بصاحبكم من جنة إن هو إلا نذير لكم بين يدي عذاب شديد )&lt;/quran_verse&gt;&lt;/cross_references&gt; &lt;source&gt;[ سبأ : 46 ]&lt;/source&gt; &lt;opinions_of_scholars&gt;يقول إنما أطلب منكم أن تقوموا لله قياما خالصا لله ، ليس فيه تعصب ولا عناد ، &lt;quran_ve" tabindex="0" style="content-visibility: hidden; transform: translate(0px, 3224px); height: 26px;"><div class="Bl"><span>```xml
&lt;tafsir_section&gt;
  &lt;tafsir_section_block&gt;
    &lt;tafsir_chunk&gt;
      &lt;opinions_of_scholars&gt;يقول تعالى : &lt;quran_verse&gt;( أولم يتفكروا )&lt;/quran_verse&gt; هؤلاء المكذبون بآياتنا &lt;quran_verse&gt;( ما بصاحبهم )&lt;/quran_verse&gt; يعني محمدا - صلوات الله وسلامه عليه &lt;quran_verse&gt;( من جنة )&lt;/quran_verse&gt; أي : ليس به جنون ، بل هو رسول الله حقا دعا إلى حق ، &lt;quran_verse&gt;( إن هو إلا نذير مبين )&lt;/quran_verse&gt; أي : ظاهر لمن كان له قلب ولب يعقل به ويعي به ،&lt;/opinions_of_scholars&gt;
    &lt;/tafsir_chunk&gt;
    &lt;tafsir_chunk&gt;
      كما قال تعالى : &lt;cross_references&gt;&lt;quran_verse&gt;( وما صاحبكم بمجنون )&lt;/quran_verse&gt;&lt;/cross_references&gt; &lt;source&gt;[ التكوير : 22 ]&lt;/source&gt; ،
    &lt;/tafsir_chunk&gt;
    &lt;tafsir_chunk&gt;
      وقال تعالى : &lt;cross_references&gt;&lt;quran_verse&gt;( قل إنما أعظكم بواحدة أن تقوموا لله مثنى وفرادى ثم تتفكروا ما بصاحبكم من جنة إن هو إلا نذير لكم بين يدي عذاب شديد )&lt;/quran_verse&gt;&lt;/cross_references&gt; &lt;source&gt;[ سبأ : 46 ]&lt;/source&gt; &lt;opinions_of_scholars&gt;يقول إنما أطلب منكم أن تقوموا لله قياما خالصا لله ، ليس فيه تعصب ولا عناد ، &lt;quran_ve</span></div></div><div class="l Zo" title="```xml
&lt;tafsir_section&gt;
  &lt;tafsir_section_block&gt;
    &lt;tafsir_chunk&gt;قول تعالى : &lt;quran_verse&gt;( أولم ينظروا )&lt;/quran_verse&gt;&lt;/tafsir_chunk&gt;
    &lt;tafsir_chunk&gt;
      &lt;opinions_of_scholars&gt;- هؤلاء المكذبون بآياتنا - في ملك الله وسلطانه في السماوات والأرض ، وفيما خلق [ الله ] من شيء فيهما ، فيتدبروا ذلك ويعتبروا به ، &lt;theological_points&gt;ويعلموا أن ذلك لمن لا نظير له ولا شبيه ، ومن فعل من لا ينبغي أن تكون العبادة والدين الخالص إلا له&lt;/theological_points&gt; فيؤمنوا به ويصدقوا رسوله ، وينيبوا إلى طاعته ، ويخلعوا الأنداد والأوثان ، ويحذروا أن تكون آجالهم قد اقتربت ، فيهلكوا على كفرهم ، ويصيروا إلى عذاب الله وأليم عقابه .&lt;/opinions_of_scholars&gt;
    &lt;/tafsir_chunk&gt;
  &lt;/tafsir_section_block&gt;
  &lt;tafsir_section_block&gt;
    &lt;tafsir_chunk&gt;وقوله : &lt;quran_verse&gt;( فبأي حديث بعده يؤمنون )&lt;/quran_verse&gt; ؟&lt;/tafsir_chunk&gt;
    &lt;tafsir_chunk&gt;
      &lt;opinions_of_scholars&gt;يقول : فبأي تخويف وتحذير وترهيب - بعد تحذير محمد وترهيبه ، الذي أتاهم به من عند الله في آي كتابه - يصدقون ، إن لم يصدقوا بهذا الحديث الذي جاءهم به محمد من عند الله ، عز و" tabindex="0" style="content-visibility: hidden; transform: translate(0px, 3250px); height: 26px;"><div class="Bl"><span>```xml
&lt;tafsir_section&gt;
  &lt;tafsir_section_block&gt;
    &lt;tafsir_chunk&gt;قول تعالى : &lt;quran_verse&gt;( أولم ينظروا )&lt;/quran_verse&gt;&lt;/tafsir_chunk&gt;
    &lt;tafsir_chunk&gt;
      &lt;opinions_of_scholars&gt;- هؤلاء المكذبون بآياتنا - في ملك الله وسلطانه في السماوات والأرض ، وفيما خلق [ الله ] من شيء فيهما ، فيتدبروا ذلك ويعتبروا به ، &lt;theological_points&gt;ويعلموا أن ذلك لمن لا نظير له ولا شبيه ، ومن فعل من لا ينبغي أن تكون العبادة والدين الخالص إلا له&lt;/theological_points&gt; فيؤمنوا به ويصدقوا رسوله ، وينيبوا إلى طاعته ، ويخلعوا الأنداد والأوثان ، ويحذروا أن تكون آجالهم قد اقتربت ، فيهلكوا على كفرهم ، ويصيروا إلى عذاب الله وأليم عقابه .&lt;/opinions_of_scholars&gt;
    &lt;/tafsir_chunk&gt;
  &lt;/tafsir_section_block&gt;
  &lt;tafsir_section_block&gt;
    &lt;tafsir_chunk&gt;وقوله : &lt;quran_verse&gt;( فبأي حديث بعده يؤمنون )&lt;/quran_verse&gt; ؟&lt;/tafsir_chunk&gt;
    &lt;tafsir_chunk&gt;
      &lt;opinions_of_scholars&gt;يقول : فبأي تخويف وتحذير وترهيب - بعد تحذير محمد وترهيبه ، الذي أتاهم به من عند الله في آي كتابه - يصدقون ، إن لم يصدقوا بهذا الحديث الذي جاءهم به محمد من عند الله ، عز و</span></div></div><div class="l" title="```xml
&lt;tafsir_section&gt;
  &lt;tafsir_section_block&gt;
    &lt;tafsir_chunk&gt;
      &lt;opinions_of_scholars&gt;
        &lt;theological_points&gt;يقول تعالى : من كتب عليه الضلالة فإنه لا يهديه أحد ، ولو نظر لنفسه فيما نظر ، فإنه لا يجزى عنه شيئا ،&lt;/theological_points&gt;
      &lt;/opinions_of_scholars&gt;
    &lt;/tafsir_chunk&gt;
    &lt;tafsir_chunk&gt;
      &lt;cross_references&gt; &lt;quran_verse&gt;( ومن يرد الله فتنته فلن تملك له من الله شيئا )&lt;/quran_verse&gt; &lt;source&gt;[ المائدة : 41 ]&lt;/source&gt;&lt;/cross_references&gt;
    &lt;/tafsir_chunk&gt;
  &lt;/tafsir_section_block&gt;
  &lt;tafsir_section_block&gt;
    &lt;tafsir_chunk&gt;
      &lt;cross_references&gt; قال تعالى : &lt;quran_verse&gt;( قل انظروا ماذا في السماوات والأرض وما تغني الآيات والنذر عن قوم لا يؤمنون )&lt;/quran_verse&gt; &lt;source&gt;[ يونس : 101 ]&lt;/source&gt;&lt;/cross_references&gt;
    &lt;/tafsir_chunk&gt;
  &lt;/tafsir_section_block&gt;
&lt;/tafsir_section&gt;
```" tabindex="0" style="content-visibility: hidden; transform: translate(0px, 3276px); height: 26px;"><div class="Bl"><span>```xml
&lt;tafsir_section&gt;
  &lt;tafsir_section_block&gt;
    &lt;tafsir_chunk&gt;
      &lt;opinions_of_scholars&gt;
        &lt;theological_points&gt;يقول تعالى : من كتب عليه الضلالة فإنه لا يهديه أحد ، ولو نظر لنفسه فيما نظر ، فإنه لا يجزى عنه شيئا ،&lt;/theological_points&gt;
      &lt;/opinions_of_scholars&gt;
    &lt;/tafsir_chunk&gt;
    &lt;tafsir_chunk&gt;
      &lt;cross_references&gt; &lt;quran_verse&gt;( ومن يرد الله فتنته فلن تملك له من الله شيئا )&lt;/quran_verse&gt; &lt;source&gt;[ المائدة : 41 ]&lt;/source&gt;&lt;/cross_references&gt;
    &lt;/tafsir_chunk&gt;
  &lt;/tafsir_section_block&gt;
  &lt;tafsir_section_block&gt;
    &lt;tafsir_chunk&gt;
      &lt;cross_references&gt; قال تعالى : &lt;quran_verse&gt;( قل انظروا ماذا في السماوات والأرض وما تغني الآيات والنذر عن قوم لا يؤمنون )&lt;/quran_verse&gt; &lt;source&gt;[ يونس : 101 ]&lt;/source&gt;&lt;/cross_references&gt;
    &lt;/tafsir_chunk&gt;
  &lt;/tafsir_section_block&gt;
&lt;/tafsir_section&gt;
```</span></div></div><div class="l Zo" title="```xml
&lt;tafsir_section&gt;
  &lt;tafsir_section_block&gt;
    &lt;tafsir_chunk&gt;
      &lt;quran_verse&gt;يقول تعالى : ( يسألونك عن الساعة )&lt;/quran_verse&gt;
      &lt;cross_references&gt;كما قال تعالى : &lt;quran_verse&gt;( يسألك الناس عن الساعة )&lt;/quran_verse&gt; [ الأحزاب : 63 ]&lt;/cross_references&gt;
    &lt;/tafsir_chunk&gt;
    &lt;tafsir_chunk&gt;
      &lt;asbab_al_nuzul&gt;قيل : نزلت في قريش . وقيل : في نفر من اليهود .&lt;/asbab_al_nuzul&gt;
      &lt;meccan_medinan&gt;والأول أشبه ; لأن الآية مكية ،&lt;/meccan_medinan&gt;
      &lt;historical_context&gt;وكانوا يسألون عن وقت الساعة ، استبعادا لوقوعها ، وتكذيبا بوجودها ;&lt;/historical_context&gt;
    &lt;/tafsir_chunk&gt;
    &lt;tafsir_chunk&gt;
      &lt;cross_references&gt;كما قال تعالى : &lt;quran_verse&gt;( ويقولون متى هذا الوعد إن كنتم صادقين )&lt;/quran_verse&gt; [ الأنبياء : 38 ] ، وقال تعالى : &lt;quran_verse&gt;( يستعجل بها الذين لا يؤمنون بها والذين آمنوا مشفقون منها ويعلمون أنها الحق ألا إن الذين يمارون في الساعة لفي ضلال بعيد )&lt;/quran_verse&gt; [ الشورى : 18 ]&lt;/cross_references&gt;
    &lt;/tafsir_chunk&gt;
  &lt;/tafsir_section_block&gt;
  &lt;tafsir_section_block&gt;
    &lt;tafsir_chu" tabindex="0" style="content-visibility: hidden; transform: translate(0px, 3302px); height: 26px;"><div class="Bl"><span>```xml
&lt;tafsir_section&gt;
  &lt;tafsir_section_block&gt;
    &lt;tafsir_chunk&gt;
      &lt;quran_verse&gt;يقول تعالى : ( يسألونك عن الساعة )&lt;/quran_verse&gt;
      &lt;cross_references&gt;كما قال تعالى : &lt;quran_verse&gt;( يسألك الناس عن الساعة )&lt;/quran_verse&gt; [ الأحزاب : 63 ]&lt;/cross_references&gt;
    &lt;/tafsir_chunk&gt;
    &lt;tafsir_chunk&gt;
      &lt;asbab_al_nuzul&gt;قيل : نزلت في قريش . وقيل : في نفر من اليهود .&lt;/asbab_al_nuzul&gt;
      &lt;meccan_medinan&gt;والأول أشبه ; لأن الآية مكية ،&lt;/meccan_medinan&gt;
      &lt;historical_context&gt;وكانوا يسألون عن وقت الساعة ، استبعادا لوقوعها ، وتكذيبا بوجودها ;&lt;/historical_context&gt;
    &lt;/tafsir_chunk&gt;
    &lt;tafsir_chunk&gt;
      &lt;cross_references&gt;كما قال تعالى : &lt;quran_verse&gt;( ويقولون متى هذا الوعد إن كنتم صادقين )&lt;/quran_verse&gt; [ الأنبياء : 38 ] ، وقال تعالى : &lt;quran_verse&gt;( يستعجل بها الذين لا يؤمنون بها والذين آمنوا مشفقون منها ويعلمون أنها الحق ألا إن الذين يمارون في الساعة لفي ضلال بعيد )&lt;/quran_verse&gt; [ الشورى : 18 ]&lt;/cross_references&gt;
    &lt;/tafsir_chunk&gt;
  &lt;/tafsir_section_block&gt;
  &lt;tafsir_section_block&gt;
    &lt;tafsir_chu</span></div></div><div class="l" title="```xml
&lt;tafsir_section&gt;
  &lt;tafsir_section_block&gt;
    &lt;tafsir_chunk&gt;
      &lt;theological_points&gt;أمره الله تعالى أن يفوض الأمور إليه ، وأن يخبر عن نفسه أنه لا يعلم الغيب ، ولا اطلاع له على شيء من ذلك إلا بما أطلعه الله عليه ،&lt;/theological_points&gt;
    &lt;/tafsir_chunk&gt;
    &lt;tafsir_chunk&gt;
      &lt;cross_references&gt;كما قال تعالى : &lt;quran_verse&gt;( عالم الغيب فلا يظهر على غيبه أحدا . [ إلا من ارتضى من رسول فإنه يسلك من بين يديه ومن خلفه رصدا ] )&lt;/quran_verse&gt; [ الجن : 26 ، 27 ]&lt;/cross_references&gt;
    &lt;/tafsir_chunk&gt;
  &lt;/tafsir_section_block&gt;
  &lt;tafsir_section_block&gt;
    &lt;tafsir_chunk&gt;
      وقوله : &lt;quran_verse&gt;( ولو كنت أعلم الغيب لاستكثرت من الخير )&lt;/quran_verse&gt;
    &lt;/tafsir_chunk&gt;
    &lt;tafsir_chunk&gt;
      &lt;source&gt;قال عبد الرزاق&lt;/source&gt; ، &lt;isnad&gt;عن الثوري ، عن منصور ، عن مجاهد .&lt;/isnad&gt;
    &lt;/tafsir_chunk&gt;
    &lt;tafsir_chunk&gt;
      &lt;quran_verse&gt;( ولو كنت أعلم الغيب لاستكثرت من الخير )&lt;/quran_verse&gt; &lt;opinions_of_scholars&gt;قال : لو كنت أعلم متى أموت ، لعملت عملا صالحا .&lt;/opinions_of_scholars&gt;
    &lt;/tafsir_chunk&gt;
  &lt;/tafsi" tabindex="0" style="content-visibility: hidden; transform: translate(0px, 3328px); height: 26px;"><div class="Bl"><span>```xml
&lt;tafsir_section&gt;
  &lt;tafsir_section_block&gt;
    &lt;tafsir_chunk&gt;
      &lt;theological_points&gt;أمره الله تعالى أن يفوض الأمور إليه ، وأن يخبر عن نفسه أنه لا يعلم الغيب ، ولا اطلاع له على شيء من ذلك إلا بما أطلعه الله عليه ،&lt;/theological_points&gt;
    &lt;/tafsir_chunk&gt;
    &lt;tafsir_chunk&gt;
      &lt;cross_references&gt;كما قال تعالى : &lt;quran_verse&gt;( عالم الغيب فلا يظهر على غيبه أحدا . [ إلا من ارتضى من رسول فإنه يسلك من بين يديه ومن خلفه رصدا ] )&lt;/quran_verse&gt; [ الجن : 26 ، 27 ]&lt;/cross_references&gt;
    &lt;/tafsir_chunk&gt;
  &lt;/tafsir_section_block&gt;
  &lt;tafsir_section_block&gt;
    &lt;tafsir_chunk&gt;
      وقوله : &lt;quran_verse&gt;( ولو كنت أعلم الغيب لاستكثرت من الخير )&lt;/quran_verse&gt;
    &lt;/tafsir_chunk&gt;
    &lt;tafsir_chunk&gt;
      &lt;source&gt;قال عبد الرزاق&lt;/source&gt; ، &lt;isnad&gt;عن الثوري ، عن منصور ، عن مجاهد .&lt;/isnad&gt;
    &lt;/tafsir_chunk&gt;
    &lt;tafsir_chunk&gt;
      &lt;quran_verse&gt;( ولو كنت أعلم الغيب لاستكثرت من الخير )&lt;/quran_verse&gt; &lt;opinions_of_scholars&gt;قال : لو كنت أعلم متى أموت ، لعملت عملا صالحا .&lt;/opinions_of_scholars&gt;
    &lt;/tafsir_chunk&gt;
  &lt;/tafsi</span></div></div><div class="l Zo" title="```xml
&lt;tafsir_section&gt;
  &lt;tafsir_section_block&gt;
    &lt;tafsir_chunk&gt;
      &lt;summary&gt;ينبه تعالى على أنه خلق جميع الناس من آدم ، عليه السلام ، وأنه خلق منه زوجه حواء ، ثم انتشر الناس منهما ،&lt;/summary&gt;
    &lt;/tafsir_chunk&gt;
    &lt;tafsir_chunk&gt;
      &lt;cross_references&gt;كما قال تعالى : &lt;quran_verse&gt;( يا أيها الناس إنا خلقناكم من ذكر وأنثى وجعلناكم شعوبا وقبائل لتعارفوا إن أكرمكم عند الله أتقاكم )&lt;/quran_verse&gt; [ الحجرات : 13 ]&lt;/cross_references&gt;
    &lt;/tafsir_chunk&gt;
    &lt;tafsir_chunk&gt;
      &lt;cross_references&gt;وقال تعالى : &lt;quran_verse&gt;( يا أيها الناس اتقوا ربكم الذي خلقكم من نفس واحدة وخلق منها زوجها [ وبث منهما رجالا كثيرا ونساء ] )&lt;/quran_verse&gt; الآية [ النساء : 1 ] .&lt;/cross_references&gt;
    &lt;/tafsir_chunk&gt;
    &lt;tafsir_chunk&gt;
      وقال في هذه الآية الكريمة : &lt;quran_verse&gt;( وجعل منها زوجها ليسكن إليها )&lt;/quran_verse&gt; &lt;linguistic_analysis&gt;أي : ليألفها ويسكن بها ،&lt;/linguistic_analysis&gt;
    &lt;/tafsir_chunk&gt;
    &lt;tafsir_chunk&gt;
      &lt;cross_references&gt;كما قال تعالى : &lt;quran_verse&gt;( ومن آياته أن خلق لكم من أنفسكم أزواجا لتسكنو" tabindex="0" style="content-visibility: hidden; transform: translate(0px, 3354px); height: 26px;"><div class="Bl"><span>```xml
&lt;tafsir_section&gt;
  &lt;tafsir_section_block&gt;
    &lt;tafsir_chunk&gt;
      &lt;summary&gt;ينبه تعالى على أنه خلق جميع الناس من آدم ، عليه السلام ، وأنه خلق منه زوجه حواء ، ثم انتشر الناس منهما ،&lt;/summary&gt;
    &lt;/tafsir_chunk&gt;
    &lt;tafsir_chunk&gt;
      &lt;cross_references&gt;كما قال تعالى : &lt;quran_verse&gt;( يا أيها الناس إنا خلقناكم من ذكر وأنثى وجعلناكم شعوبا وقبائل لتعارفوا إن أكرمكم عند الله أتقاكم )&lt;/quran_verse&gt; [ الحجرات : 13 ]&lt;/cross_references&gt;
    &lt;/tafsir_chunk&gt;
    &lt;tafsir_chunk&gt;
      &lt;cross_references&gt;وقال تعالى : &lt;quran_verse&gt;( يا أيها الناس اتقوا ربكم الذي خلقكم من نفس واحدة وخلق منها زوجها [ وبث منهما رجالا كثيرا ونساء ] )&lt;/quran_verse&gt; الآية [ النساء : 1 ] .&lt;/cross_references&gt;
    &lt;/tafsir_chunk&gt;
    &lt;tafsir_chunk&gt;
      وقال في هذه الآية الكريمة : &lt;quran_verse&gt;( وجعل منها زوجها ليسكن إليها )&lt;/quran_verse&gt; &lt;linguistic_analysis&gt;أي : ليألفها ويسكن بها ،&lt;/linguistic_analysis&gt;
    &lt;/tafsir_chunk&gt;
    &lt;tafsir_chunk&gt;
      &lt;cross_references&gt;كما قال تعالى : &lt;quran_verse&gt;( ومن آياته أن خلق لكم من أنفسكم أزواجا لتسكنو</span></div></div><div class="l" title="```xml
&lt;tafsir_section&gt;
  &lt;tafsir_section_block&gt;
    &lt;tafsir_chunk&gt;
      &lt;quran_verse&gt;( فلما آتاهما صالحا جعلا له شركاء فيما آتاهما فتعالى الله عما يشركون )&lt;/quran_verse&gt;
    &lt;/tafsir_chunk&gt;
    &lt;tafsir_chunk&gt;
      &lt;methodological_notes&gt;ذكر المفسرون هاهنا آثارا وأحاديث سأوردها وأبين ما فيها ، ثم نتبع ذلك بيان الصحيح في ذلك ، إن شاء الله وبه الثقة .&lt;/methodological_notes&gt;
    &lt;/tafsir_chunk&gt;
  &lt;/tafsir_section_block&gt;
  &lt;tafsir_section_block&gt;
    &lt;tafsir_chunk&gt;
      &lt;source&gt;قال الإمام أحمد في مسنده :&lt;/source&gt;
      &lt;isnad&gt;حدثنا عبد الصمد ، حدثنا عمر بن إبراهيم ، حدثنا قتادة ، عن الحسن ، عن سمرة ، عن النبي صلى الله عليه وسلم قال :&lt;/isnad&gt;
      &lt;hadith&gt;&quot; ولما ولدت حواء طاف بها إبليس - وكان لا يعيش لها ولد - فقال : سميه عبد الحارث ; فإنه يعيش ، فسمته عبد الحارث ، فعاش وكان ذلك من وحي الشيطان وأمره &quot; .&lt;/hadith&gt;
    &lt;/tafsir_chunk&gt;
    &lt;tafsir_chunk&gt;
      &lt;hadith_support&gt;
        &lt;source&gt;وهكذا رواه ابن جرير ،&lt;/source&gt;
        &lt;isnad&gt;عن محمد بن بشار بندار ، عن عبد الصمد بن عبد الوارث ، به .&lt;/isnad&gt;
      &lt;/hadit" tabindex="0" style="content-visibility: hidden; transform: translate(0px, 3380px); height: 26px;"><div class="Bl"><span>```xml
&lt;tafsir_section&gt;
  &lt;tafsir_section_block&gt;
    &lt;tafsir_chunk&gt;
      &lt;quran_verse&gt;( فلما آتاهما صالحا جعلا له شركاء فيما آتاهما فتعالى الله عما يشركون )&lt;/quran_verse&gt;
    &lt;/tafsir_chunk&gt;
    &lt;tafsir_chunk&gt;
      &lt;methodological_notes&gt;ذكر المفسرون هاهنا آثارا وأحاديث سأوردها وأبين ما فيها ، ثم نتبع ذلك بيان الصحيح في ذلك ، إن شاء الله وبه الثقة .&lt;/methodological_notes&gt;
    &lt;/tafsir_chunk&gt;
  &lt;/tafsir_section_block&gt;
  &lt;tafsir_section_block&gt;
    &lt;tafsir_chunk&gt;
      &lt;source&gt;قال الإمام أحمد في مسنده :&lt;/source&gt;
      &lt;isnad&gt;حدثنا عبد الصمد ، حدثنا عمر بن إبراهيم ، حدثنا قتادة ، عن الحسن ، عن سمرة ، عن النبي صلى الله عليه وسلم قال :&lt;/isnad&gt;
      &lt;hadith&gt;" ولما ولدت حواء طاف بها إبليس - وكان لا يعيش لها ولد - فقال : سميه عبد الحارث ; فإنه يعيش ، فسمته عبد الحارث ، فعاش وكان ذلك من وحي الشيطان وأمره " .&lt;/hadith&gt;
    &lt;/tafsir_chunk&gt;
    &lt;tafsir_chunk&gt;
      &lt;hadith_support&gt;
        &lt;source&gt;وهكذا رواه ابن جرير ،&lt;/source&gt;
        &lt;isnad&gt;عن محمد بن بشار بندار ، عن عبد الصمد بن عبد الوارث ، به .&lt;/isnad&gt;
      &lt;/hadit</span></div></div></div>
"""


def extract_tafsir_sections(html_content):
    """
    تستخرج هذه الدالة جميع النصوص التي تبدأ بـ <tafsir_section>
    وتنتهي بـ </tafsir_section> شاملة الأوسمة (tags).
    """
    soup = BeautifulSoup(html_content, "html.parser")
    results = []

    for element in soup.find_all("div", class_=re.compile(r"\b(l|Bl)\b")):
        text = element.get("title", "") or element.get_text()
        pattern = r"<tafsir_section>.*?</tafsir_section>"
        matches = re.findall(pattern, text, re.DOTALL)

        results.extend(matches)

    return results
